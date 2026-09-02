# 피싱브레이크 (Phishing Break)

2026 금융 AI Challenge — 보이스피싱 판별 어시스턴트 MVP

## 폴더 구조

```
phishing_break/
├── backend/
│   ├── main.py           # FastAPI 앱 (API + 정적 파일 서빙)
│   ├── analyzer.py       # 핵심 판별 로직 (Claude API 호출)
│   ├── masking.py        # 개인정보 마스킹
│   ├── knowledge_base.py # 사기 유형/단계 참조 지식
│   ├── samples.py        # 데모용 샘플 시나리오
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── .env.example
```

## VSCode에서 실행하기

### 1. 프로�트 열기
VSCode에서 `phishing_break` 폴더를 통째로 열기 (File → Open Folder)

### 2. 파이썬 가상환경 생성 (터미널에서)
```bash
cd phishing_break/backend
python -m venv venv

# Mac/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

VSCode 우측 하단에서 인터프리터를 방금 만든 `venv`로 선택하세요.

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. API 키 설정 (.env 파일 방식 — 터미널마다 다시 입력할 필요 없음)

`backend` 폴더 안에 `.env` 라는 이름의 새 파일을 만들고, 아래처럼 한 줄만 적으세요 (`.env.example` 참고):

```
GEMINI_API_KEY=본인키
```

큰따옴표 없이, `=` 뒤에 바로 키 값을 붙여서 적으면 됩니다. 이 파일은 서버가 자동으로 읽어오기 때문에, 앞으로는 터미널을 새로 열어도 `$env:GEMINI_API_KEY=...`를 매번 다시 칠 필요가 없습니다.

API 키는 https://aistudio.google.com/apikey 에서 구글 계정으로 로그인 후 **무료로** 발급받습니다. 결제 정보 등록이 필요 없고, Flash 계열 모델은 무료 티어로 충분히 테스트 가능합니다. (단, 무료 티어는 분당/일일 요청 횟수 제한이 있으니 팀 전체가 짧은 시간에 몰아서 테스트하면 429 오류가 날 수 있습니다 — 이 경우 잠시 기다렸다가 재시도하세요.)

⚠️ `.env` 파일은 API 키가 담긴 비밀 파일이니, GitHub에 올릴 때 반드시 `.gitignore`에 추가해서 제외하세요.

### 5. 서버 실행
```bash
uvicorn main:app --reload
```

### 6. 접속
브라우저에서 http://127.0.0.1:8000 접속

## 배포 (심사 제출용 URL 필요 시)

무료로 배포하려면 아래 중 하나를 추천합니다:
- **Render.com**: FastAPI를 그대로 무료 배포 가능, 환경변수(`GEMINI_API_KEY`)도 대시보드에서 등록
- **Railway.app**: 비슷한 방식, GitHub 연동 배포

로컬에서 동작 확인 후, GitHub에 푸시 → 위 서비스에 연결 → 환경변수에 `GEMINI_API_KEY` 등록하면 배포 URL이 생깁니다.

## 사용 모델

`gemini-3.6-flash` (무료 티어 포함, 결제 정보 불필요). Gemini는 모델이 자주 업데이트되므로, 나중에 404/503 에러가 나면 에러 메시지에 뜨는 대체 모델명을 `backend/analyzer.py`의 `MODEL` 변수에 그대로 넣으면 됩니다.

## 지금 구현된 것 (1순위 + 2순위)

- [x] 텍스트 입력 → AI 판별 → 결과 화면
- [x] 개인정보 마스킹
- [x] 사기 유형 / 진행 단계 / 위험도 점수
- [x] 근거 문장 인용 (원문에서만 인용하도록 프롬프트 제약)
- [x] 다음 수순 예측
- [x] 대응 가이드 + 공유 문구 생성 + 복사 버튼
- [x] 샘플 사례 3종 버튼

## 아직 안 만든 것 (기능명세서 작성 시 빼야 할 항목)

- [ ] 회원가입/로그인
- [ ] 데이터 영구 저장 (DB)
- [ ] 통화 실시간 감지
- [ ] 이미지/음성 입력 (OCR 등)
