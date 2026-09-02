"""
피싱브레이크 핵심 분석 로직 (Gemini API 버전)
1. PII 마스킹
2. 참조 지식(유형/단계 정의)을 프롬프트에 주입
3. response_schema로 JSON 구조를 강제해 안정적인 응답을 받음 (response.parsed)
4. 근거 문장은 반드시 입력 원문에서 인용하도록 프롬프트로 제약(환각 방지)

필요한 환경변수: GEMINI_API_KEY (https://aistudio.google.com/apikey 에서 발급, 결제 정보 불필요)
"""
import os
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from masking import mask_pii
from knowledge_base import build_reference_block
from link_checker import check_links, build_summary_for_prompt

import time

# 'gemini-flash-latest'는 최신(=혼잡한) 모델을 가리켜 503 에러가 잦았고,
# 'gemini-2.5-flash'는 신규 사용자 대상 서비스가 종료됨(404).
# 현재 정상 동작 확인된 모델로 고정.
MODEL = "gemini-3.1-flash-lite"


class PhishingAnalysis(BaseModel):
    """구조화된 판별 결과. 필드를 중첩 없이 평평하게 유지해야 스키마 변환이 안정적이다."""
    scam_type: str = Field(description="기관사칭 / 대출빙자 / 가족지인사칭 / 투자리딩방 / 정상 중 하나")
    stage: int = Field(ge=0, le=5, description="시나리오 진행 단계(1~5). 정상이면 0.")
    risk_score: int = Field(ge=0, le=100, description="위험도 점수. 높을수록 위험.")
    evidence_quotes: List[str] = Field(description="판단 근거가 된 입력 원문 문장. 반드시 원문에 실제로 존재하는 문장만.")
    predicted_next_moves: List[str] = Field(description="상대가 다음에 요구할 가능성이 높은 행동 2~3개. 정상이면 빈 배열.")
    response_guide: str = Field(description="사용자가 지금 즉시 취해야 할 행동 안내 (2~4문장)")
    share_message: str = Field(description="가족·은행 상담원에게 전달할 공유용 메시지. 정상이면 빈 문자열.")


SYSTEM_PROMPT = """당신은 금융사기(보이스피싱) 판별 전문가입니다.
사용자가 받은 문자·메신저 대화·통화 내용을 분석하여 사기 여부를 판별합니다.

{reference}

판별 원칙:
- evidence_quotes는 반드시 입력 원문에 실제로 존재하는 문장만 그대로 인용하세요. 없는 내용을 지어내지 마세요.
- 정상적인 안내문(예: 만기 안내, 결제 알림)과 사기를 혼동하지 마세요. "비밀유지 요구", "긴급 송금 압박", "원격제어 앱 설치 요구" 같은 신호가 없으면 정상으로 판별하세요.
- risk_score는 사기 신호의 개수와 강도에 비례하게 산정하세요. 정상은 30점 이하, 명백한 사기는 70점 이상을 권장합니다.
- predicted_next_moves는 해당 유형의 전형적인 다음 단계를 근거로 구체적으로 작성하세요.
- response_guide는 겁을 주지 않으면서도 명확하게, 지금 당장 할 행동을 안내하세요 (예: 통화 종료, 공식 대표번호로 재확인, 112/1332 신고).
- scam_type은 반드시 "기관사칭", "대출빙자", "가족지인사칭", "투자리딩방", "정상" 중 하나로만 답하세요.
- 만약 [시스템이 사전 분석한 링크 정보]가 함께 제공되면, 그 링크가 "위험" 또는 "의심"으로 표시된 경우 이를 사기의 강력한 근거로 반영해 risk_score를 높이고, response_guide에도 "해당 링크를 절대 클릭하지 말 것"을 명시하세요.
""".format(reference=build_reference_block())

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = genai.Client(api_key=api_key)
    return _client


def analyze_conversation(raw_text: str) -> dict:
    """대화 텍스트를 분석하여 구조화된 판별 결과를 반환한다.
    구글 서버 과부하(503)로 인한 일시적 실패는 최대 3회까지 짧게 재시도한다."""
    if not raw_text or not raw_text.strip():
        raise ValueError("분석할 텍스트가 비어 있습니다.")

    # 링크는 원문(마스킹 전)에서 분석한다 — URL 구조를 그대로 봐야 정확하다.
    link_results = check_links(raw_text)
    link_summary = build_summary_for_prompt(link_results)

    masked_text = mask_pii(raw_text)
    client = _get_client()

    user_content = f"다음 대화를 분석해주세요:\n\n{masked_text}"
    if link_summary:
        user_content += f"\n\n{link_summary}"

    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=PhishingAnalysis,
                    temperature=0.2,
                ),
            )
            parsed: PhishingAnalysis = response.parsed
            if parsed is None:
                raise RuntimeError("모델이 예상된 형식으로 응답하지 않았습니다. 원본 응답: " + str(response.text))

            result = parsed.model_dump()
            result["masked_input"] = masked_text  # 마스킹 확인용 (프론트 미표시 가능)
            result["link_findings"] = link_results  # 휴리스틱 기반 결정론적 결과 (환각 없음)
            return result

        except Exception as e:
            last_error = e
            is_overloaded = "503" in str(e) or "UNAVAILABLE" in str(e)
            if is_overloaded and attempt < 2:
                time.sleep(2 * (attempt + 1))  # 2초, 4초 대기 후 재시도
                continue
            raise

    raise last_error


def extract_text_from_image(image_bytes: bytes, mime_type: str) -> str:
    """대화 스크린샷 이미지에서 텍스트를 추출한다 (Gemini의 이미지 인식 기능 사용)."""
    client = _get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            (
                "이 이미지는 문자메시지 또는 카카오톡 등 메신저 대화를 캡처한 스크린샷입니다. "
                "화면에 보이는 대화 내용을 순서대로 그대로 텍스트로 옮겨 적어주세요. "
                "발신자 이름(예: '우리딸')이 보이면 그 앞에 표기해주세요. "
                "대화 내용 텍스트만 출력하고, 다른 설명이나 인사말은 절대 덧붙이지 마세요."
            ),
        ],
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return (response.text or "").strip()


def analyze_image(image_bytes: bytes, mime_type: str, extra_text: str = "") -> dict:
    """이미지(대화 스크린샷)를 텍스트로 추출한 뒤, 기존 텍스트 분석 파이프라인을 그대로 재사용한다.
    extra_text가 함께 주어지면(예: 사용자가 상황을 보충 설명한 경우) 추출된 대화 뒤에 이어붙여 함께 분석한다."""
    extracted_text = extract_text_from_image(image_bytes, mime_type)
    if not extracted_text:
        raise ValueError("이미지에서 대화 내용을 추출하지 못했습니다. 텍스트가 선명하게 보이는 스크린샷인지 확인해주세요.")

    combined_text = extracted_text
    extra_text = (extra_text or "").strip()
    if extra_text:
        combined_text = f"{extracted_text}\n\n[사용자가 추가로 남긴 설명]\n{extra_text}"

    result = analyze_conversation(combined_text)
    result["extracted_text"] = extracted_text  # 사용자가 인식 결과를 눈으로 확인할 수 있도록 포함
    return result