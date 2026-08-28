"""Agent Job Coach（Agent 求职助手）· FastAPI 入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, interview, kb
from app.config import config
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("[Agent Job Coach] MySQL 表已就绪")
    yield


app = FastAPI(title=config.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(interview.router)
app.include_router(kb.router)


@app.get("/")
async def root():
    return {
        "app": config.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "api": {
            "chat_stream": "POST /api/agent/chat_stream",
            "chat": "POST /api/agent/chat",
            "interview_start": "POST /api/interview/start",
            "interview_answer": "POST /api/interview/answer",
            "kb_search": "GET /api/kb/search",
            "kb_upload": "POST /api/kb/upload",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
