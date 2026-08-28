"""Chroma 向量库：单 collection + metadata category 分类过滤

v2：collection 改名 agent_job_coach_kb；提供缓存失效钩子供 search 层使用。
"""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.agent.llm import get_embeddings
from app.config import config

_COLLECTION = "agent_job_coach_kb"
_store: Chroma | None = None


def get_store() -> Chroma:
    """单例：Chroma 持久化向量库"""
    global _store
    if _store is None:
        Path(config.kb_vector_dir).mkdir(parents=True, exist_ok=True)
        _store = Chroma(
            collection_name=_COLLECTION,
            embedding_function=get_embeddings(),
            persist_directory=config.kb_vector_dir,
        )
    return _store


def add_documents(docs: list[Document]) -> None:
    if docs:
        get_store().add_documents(docs)
        invalidate()


def delete_by_source(source: str) -> None:
    """按来源删除（知识库重建/单文件重灌用），删除后失效语料缓存"""
    get_store().delete(where={"source": source})
    invalidate()


def invalidate() -> None:
    """让 search 层 BM25 语料缓存失效（import 延迟避免循环依赖）"""
    from app.rag.search import invalidate_corpus

    invalidate_corpus()


def clear() -> None:
    """清空向量库（重建知识库时用）"""
    get_store().delete_collection()
    _store_holder()


def _store_holder() -> None:
    global _store
    _store = None
