"""混合检索：向量（语义）+ BM25（关键词）→ RRF 融合，支持分类过滤与来源溯源"""

import math
import re
from collections import Counter

from app.config import config
from app.rag.store import get_store

_LATIN_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_corpus_cache: dict[str, list[dict] | None] = {}


def _tokenize(text: str) -> list[str]:
    """轻量分词：英文/数字词 + 中文二元组"""
    text = text.lower()
    toks = _LATIN_RE.findall(text)
    cjk = _CJK_RE.findall(text)
    toks.extend("".join(cjk[i : i + 2]) for i in range(len(cjk) - 1))
    return toks


def _bm25_scores(query: str, corpus: list[dict], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(corpus)
    if n == 0:
        return []
    lens = [len(c["content"]) for c in corpus]
    avgdl = sum(lens) / n
    q_terms = set(_tokenize(query))
    if not q_terms:
        return [0.0] * n
    df: Counter = Counter()
    doc_tf: list[Counter] = []
    for c in corpus:
        toks = _tokenize(c["content"])
        doc_tf.append(Counter(toks))
        for t in set(toks):
            df[t] += 1
    scores = []
    for i, tf in enumerate(doc_tf):
        s = 0.0
        dl = lens[i]
        for t in q_terms:
            f = tf.get(t, 0)
            if f == 0:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    return scores


def _load_corpus(category: str | None = None) -> list[dict]:
    """从 Chroma 拉取全部片段作为 BM25 语料（按 category 缓存，add/delete 后失效）"""
    cache_key = category or "__all__"
    if cache_key in _corpus_cache and _corpus_cache[cache_key] is not None:
        return _corpus_cache[cache_key]
    try:
        where = {"category": category} if category else None
        got = get_store().get(where=where, include=["documents", "metadatas"])
        ids = got.get("ids") or []
        docs = got.get("documents") or []
        metas = got.get("metadatas") or []
        corpus = [
            {"content": str(docs[i]), "meta": metas[i] or {}} for i in range(len(ids))
        ]
        _corpus_cache[cache_key] = corpus
        return corpus
    except Exception:
        return []


def invalidate_corpus() -> None:
    """知识库增删后调用，清空 BM25 语料缓存"""
    _corpus_cache.clear()


def _format_result(content: str, meta: dict, score: float) -> dict:
    return {
        "content": content,
        "source": meta.get("source", "未知来源"),
        "category": meta.get("category", ""),
        "category_name": meta.get("category_name", ""),
        "section": meta.get("section", ""),
        "score": round(score, 4),
    }


def hybrid_search(query: str, k: int | None = None, category: str | None = None) -> list[dict]:
    """向量 top-N + BM25 top-N → RRF 融合 → top-k"""
    k = k or config.kb_top_k
    store = get_store()
    filter_ = {"category": category} if category else None
    vector_results = store.similarity_search(query, k=max(k * 3, 20), filter=filter_)
    corpus = _load_corpus(category)
    if not corpus:
        return [
            _format_result(doc.page_content, doc.metadata, 0.0)
            for doc in vector_results[:k]
        ]

    content_idx = {c["content"]: i for i, c in enumerate(corpus)}
    bm = _bm25_scores(query, corpus)
    bm_rank = sorted(range(len(corpus)), key=lambda i: bm[i], reverse=True)[: max(k * 3, 20)]

    rrf: dict[int, float] = {}
    for rank, doc in enumerate(vector_results):
        idx = content_idx.get(doc.page_content)
        if idx is not None:
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (60 + rank)
    for rank, idx in enumerate(bm_rank):
        rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (60 + rank)

    top = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)[:k]
    items = []
    for idx, s in top:
        meta = corpus[idx]["meta"]
        items.append(_format_result(corpus[idx]["content"], meta, min(s * 30.0, 1.0)))
    return items


def search_as_context(query: str, k: int | None = None, category: str | None = None) -> str:
    """检索并格式化为 LLM 友好的上下文（带来源/章节）"""
    items = hybrid_search(query, k, category)
    if not items:
        return "没有找到相关资料。"
    parts = []
    for i, item in enumerate(items, 1):
        header = f"【资料 {i} | 来源: {item['source']} | {item['category_name']}"
        if item.get("section"):
            header += f" | {item['section']}"
        parts.append(f"{header}】\n{item['content']}")
    return "\n\n".join(parts)
