"""
피싱브레이크 FastAPI 백엔드.

실행:
    cd backend
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...   (Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-...")
    uvicorn main:app --reload

실행 후 http://127.0.0.1:8000 접속
"""
import os
from dotenv import load_dotenv

# backend 폴더의 .env 파일을 자동으로 읽어서 환경변수로 등록.
# 이렇게 하면 터미널을 새로 열 때마다 $env:GEMINI_API_KEY를 다시 칠 필요가 없다.
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from analyzer import analyze_conversation, analyze_image
from samples import SAMPLES

app = FastAPI(title="피싱브레이크 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 데모 목적. 실서비스에서는 허용 도메인을 제한할 것.
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        result = analyze_conversation(req.text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 데모 단계에서는 원인 파악을 위해 에러 메시지를 그대로 노출.
        # 실서비스 배포 시에는 상세 메시지를 감추는 것을 권장.
        raise HTTPException(status_code=500, detail=f"분석 중 오류가 발생했습니다: {e}")


@app.get("/api/samples")
def get_samples():
    return SAMPLES


@app.post("/api/analyze-image")
async def analyze_image_endpoint(file: UploadFile = File(...), text: str = Form("")):
    # 허용 이미지 타입만 처리 (실수로 다른 파일이 올라오는 것 방지)
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다: {file.content_type}")

    # 용량 제한 (10MB) — 너무 큰 파일로 인한 지연/오류 방지
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="이미지 용량이 너무 큽니다 (10MB 이하만 지원).")

    try:
        result = analyze_image(image_bytes, file.content_type, extra_text=text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 중 오류가 발생했습니다: {e}")


# 프론트엔드 정적 파일 서빙 (프로젝트 루트의 frontend 폴더)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))