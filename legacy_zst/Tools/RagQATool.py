import math
import re
from collections import Counter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from Models.Factory import llm
from Tools.VecStore import VecStore

vec = VecStore()
db = vec.load_chroma()


# ---------------------------------------------------------------------------
# 混合检索：向量（语义） + BM25（关键词） → RRF 融合
# 移植自仓维云 backend/app/services/kb_service.py
# ---------------------------------------------------------------------------
_LATIN_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _tokenize(text: str) -> list[str]:
    """轻量分词：英文/数字词 + 中文二元组（无 jieba 依赖的近似方案）"""
    text = text.lower()
    toks = _LATIN_RE.findall(text)
    cjk = _CJK_RE.findall(text)
    toks.extend("".join(cjk[i : i + 2]) for i in range(len(cjk) - 1))
    return toks


def _bm25_scores(query: str, corpus: list[dict], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """BM25 关键词打分（自实现，无 rank_bm25 依赖）"""
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


def hybrid_search(query: str, k: int = 5) -> list[dict]:
    """向量 top-N + BM25 top-N → RRF 融合 → top-k"""
    vector_results = db.similarity_search(query, k=max(k * 3, 20))
    try:
        got = db.get(include=["documents", "metadatas"])
        ids = got.get("ids") or []
        docs = got.get("documents") or []
        metas = got.get("metadatas") or []
        corpus = [
            {"content": str(docs[i]), "meta": metas[i] or {}} for i in range(len(ids))
        ]
    except Exception as exc:  # 语料加载失败回退纯向量
        print(f"[RAG] 全文语料加载失败，回退纯向量检索: {exc}")
        corpus = []

    if not corpus:
        return [
            {"content": doc.page_content, "meta": doc.metadata}
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
    return [
        {"content": corpus[idx]["content"], "meta": corpus[idx]["meta"]}
        for idx, _score in top
    ]


def _format_context(items: list[dict]) -> str:
    """把检索结果格式化为 LLM 友好的上下文（带来源/章节）"""
    parts = []
    for i, item in enumerate(items, 1):
        meta = item["meta"]
        header = f"【资料 {i} | 来源: {meta.get('source', '未知')}"
        if meta.get("section"):
            header += f" | {meta['section']}"
        if meta.get("page") is not None:
            header += f" | 第{meta['page']}页"
        parts.append(f"{header}】\n{item['content']}")
    return "\n\n".join(parts)


_QA_TEMPLATE = """基于以下已知信息，简洁和专业的回答用户的问题。不允许在答案中添加编造成分。
已知内容:
{context}

问题:
{question}
"""


def rag_qa(query):
    """混合检索增强问答：向量 + BM25 双路召回 → RRF 融合 → DeepSeek 生成"""
    items = hybrid_search(query, k=5)
    context = _format_context(items)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=_QA_TEMPLATE,
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context, "question": query})
