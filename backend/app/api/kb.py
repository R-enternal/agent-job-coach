"""知识库 API：检索 / 列表 / 上传入库"""

from pathlib import Path

from fastapi import APIRouter, UploadFile

from app.rag.loader import CATEGORY_NAMES, parse_file
from app.rag.search import hybrid_search
from app.rag.store import add_documents

router = APIRouter(prefix="/api/kb", tags=["知识库"])


@router.get("/search")
async def search(q: str, category: str = "", k: int = 5):
    items = hybrid_search(q, k=k, category=category or None)
    return {"query": q, "items": items}


@router.get("/categories")
async def categories():
    return CATEGORY_NAMES


@router.post("/upload")
async def upload(category: str, file: UploadFile):
    """上传文件到知识库（resume/jd/project/interview），解析切块入库"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".md", ".txt", ".html", ".pdf", ".docx", ".markdown"):
        return {"error": f"不支持的文件类型 {suffix}"}
    data = await file.read()
    tmp = Path("_upload_tmp") / f"{category}_{file.filename}"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_bytes(data)
    docs = parse_file(tmp, category)
    if docs:
        add_documents(docs)
    tmp.unlink(missing_ok=True)
    return {"filename": file.filename, "category": category, "chunks": len(docs)}
