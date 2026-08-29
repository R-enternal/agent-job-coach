"""知识库 API：检索 / 列表 / 上传入库"""

from pathlib import Path

from fastapi import APIRouter, UploadFile

from app.rag.loader import CATEGORY_NAMES, parse_file
from app.rag.search import hybrid_search
from app.rag.store import add_documents, delete_by_source, get_store

router = APIRouter(prefix="/api/kb", tags=["知识库"])


@router.get("/documents")
async def documents():
    """知识库文档列表：按 source（文件名）聚合，返回分类与块数"""
    data = get_store().get(include=["metadatas"])
    agg: dict[str, dict] = {}
    for meta in data.get("metadatas") or []:
        meta = meta or {}
        src = str(meta.get("source", "未知来源"))
        a = agg.setdefault(src, {
            "source": src,
            "category": str(meta.get("category", "")),
            "category_name": str(meta.get("category_name", "")),
            "chunks": 0,
        })
        a["chunks"] += 1
    items = sorted(agg.values(), key=lambda x: (x["category"], x["source"]))
    return {"items": items, "total_chunks": sum(a["chunks"] for a in items)}


@router.delete("/documents")
async def delete_document(source: str):
    """按来源文件名删除文档的全部切块"""
    delete_by_source(source)
    return {"deleted": source}


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
