"""Agent Job Coach（Agent 求职助手）· FastAPI 入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.qa_agent import init_qa_graph
from app.api import assets, chat, interview, jd, kb, qlist
from app.config import config
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("[Agent Job Coach] MySQL 表已就绪")
    # QA 图状态存档：AsyncSqliteSaver（需在运行中的事件循环内构造，故放 lifespan）
    db_path = config.qa_checkpoint_db
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        await saver.setup()  # 幂等建表；读写方法内部也有惰性 setup，这里显式提前失败
        init_qa_graph(saver)
        print(f"[Agent Job Coach] QA 图已挂 AsyncSqliteSaver：{db_path}")
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
app.include_router(assets.router)
app.include_router(jd.router)
app.include_router(qlist.router)


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
            "assets_resume": "POST/GET /api/assets/resume",
            "assets_projects": "POST/GET /api/assets/projects（POST /extract 抽取草稿）",
            "jd_parse": "POST /api/jd/parse | POST /api/jd/parse_image（draft → PUT 确认）",
            "qlist": "POST /api/qlist/generate | GET /api/qlist/{id}",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
