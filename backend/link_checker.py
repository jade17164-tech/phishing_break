"""
URL/링크 위험도 휴리스틱 분석기.
실제로 링크에 접속하지 않고, URL 구조만 보고 위험 신호를 판별한다.
(직접 방문은 위험하므로 하지 않음 — 텍스트 패턴 분석만 수행)
"""
import re
from typing import List, Dict
from urllib.parse import urlparse

URL_PATTERN = re.compile(
    r'(https?://[^\s]+|(?<![\w.])(?:[a-zA-Z0-9-]+\.)+(?:kr|com|net|org|co|xyz|top|click|work|support|info|me|io|live|icu)(?:/[^\s]*)?)',
    re.IGNORECASE,
)

SHORTENER_DOMAINS = {
    "bit.ly", "tinyurl.com", "han.gl", "vo.la", "url.kr", "me2.do",
    "goo.gl", "t.co", "is.gd", "buff.ly", "bitly.com",
    # 국내에서 스미싱에 자주 악용되는 단축 URL 서비스 추가
    "reurl.kr", "kko.to", "kus.kr", "me2.kr", "dwz.kr", "t2m.kr",
    "1.ug", "v.gd", "tiny.cc", "shorturl.at", "cutt.ly", "s.id", "rb.gy",
}

SUSPICIOUS_TLDS = {".xyz", ".top", ".click", ".work", ".support", ".cf", ".tk", ".gq", ".ml", ".live", ".icu"}

# 자주 사칭되는 브랜드 키워드: 값은 실제 공식 도메인 목록.
# URL에 키워드는 포함되어 있는데 공식 도메인이 아니면 사칭 의심.
IMPERSONATION_KEYWORDS = {
    "kbstar": ["kbstar.com"],
    "국민은행": ["kbstar.com"],
    "toss": ["toss.im"],
    "카카오뱅크": ["kakaobank.com"],
    "kakaobank": ["kakaobank.com"],
    "금융감독원": ["fss.or.kr"],
    "fss": ["fss.or.kr"],
    "경찰청": ["police.go.kr"],
    "police": ["police.go.kr"],
    "국세청": ["nts.go.kr"],
}

# 목록에 없는 새 단축 URL 서비스도 잡기 위한 안전장치.
# 이 도메인들은 이름이 짧아도 "단축 URL 의심"으로 오탐되지 않도록 예외 처리.
KNOWN_SAFE_SHORT_DOMAINS = {d for domains in IMPERSONATION_KEYWORDS.values() for d in domains}


def extract_urls(text: str) -> List[str]:
    """텍스트에서 URL로 추정되는 문자열을 모두 추출한다."""
    seen = []
    for m in URL_PATTERN.finditer(text):
        url = m.group(0).rstrip(".,!?)")  # 문장부호가 같이 붙는 경우 제거
        if url not in seen:
            seen.append(url)
    return seen


def _normalize(url: str) -> str:
    if not url.startswith("http"):
        url = "http://" + url
    return url


def analyze_url(url: str) -> Dict:
    """단일 URL의 위험 신호를 분석한다."""
    reasons = []
    risk = "안전"

    parsed = urlparse(_normalize(url))
    host = (parsed.hostname or "").lower()

    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        reasons.append("도메인이 아닌 IP 주소를 직접 사용함")
        risk = "위험"

    if host in SHORTENER_DOMAINS:
        reasons.append("단축 URL 서비스 사용 (실제 목적지를 숨김)")
        risk = "의심" if risk == "안전" else risk
    elif not any(host.endswith(d) for d in KNOWN_SAFE_SHORT_DOMAINS):
        # 목록에 없는 도메인이어도, 도메인 이름 자체가 비정상적으로 짧으면
        # 신종 단축 URL 서비스일 가능성이 높음 (예: reurl.kr, kus.kr 등은 대부분 5자 이하)
        label = host.split(".")[0] if host else ""
        if 0 < len(label) <= 5:
            reasons.append(f"도메인 이름이 매우 짧음('{label}') — 목록에 없는 단축 URL 서비스일 가능성")
            risk = "의심" if risk == "안전" else risk

    for tld in SUSPICIOUS_TLDS:
        if host.endswith(tld):
            reasons.append(f"스팸/피싱에 자주 악용되는 도메인({tld})")
            risk = "위험"
            break

    if url.lower().split("?")[0].endswith(".apk"):
        reasons.append("APK 파일 직접 설치 유도 (공식 앱스토어 우회)")
        risk = "위험"

    for keyword, official_domains in IMPERSONATION_KEYWORDS.items():
        if keyword in url.lower() and not any(host.endswith(d) for d in official_domains):
            reasons.append(f"'{keyword}' 명칭을 포함하지만 공식 도메인이 아님 (사칭 의심)")
            risk = "위험"
            break

    if not reasons:
        reasons.append("뚜렷한 위험 신호는 없으나, 실제 클릭 전 항상 주의가 필요함")

    return {"url": url, "risk": risk, "reasons": reasons}


def check_links(text: str) -> List[Dict]:
    """텍스트 안의 모든 URL을 찾아 각각 위험도를 분석해 반환한다."""
    return [analyze_url(u) for u in extract_urls(text)]


def build_summary_for_prompt(link_results: List[Dict]) -> str:
    """LLM 프롬프트에 주입할 링크 분석 요약 텍스트를 만든다."""
    if not link_results:
        return ""
    lines = ["[시스템이 사전 분석한 링크 정보 — 이 정보를 위험도 판단에 반영할 것]"]
    for r in link_results:
        lines.append(f"- {r['url']} → {r['risk']} ({', '.join(r['reasons'])})")
    return "\n".join(lines)