"""题单生成：JD 要求 + 个人素材 + 题库检索（按题型配额）→ LLM 定制出题 → 落库

补齐策略（已与 Codex 确认）：LLM 出题不足配额时，允许用题库检索结果直接补齐，
并标注 source=kb 与 LLM 生成（source=llm）区分。
"""

import json

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.llm import call_llm_json
from app.constants import TOPIC_NAMES
from app.models import JdEntry, QuestionList
from app.rag.search import hybrid_search, search_as_context
from app.services.assets import get_resume, list_projects
from app.services.jd import parsed_to_text

_DEFAULT_QUOTA: dict[str, int] = {"agent": 2, "rag": 2, "project": 2, "eight-part": 2, "hr": 1}

_GEN_PROMPT = """你是资深技术面试官，为候选人生成定制面试题单。

【岗位要求】
{jd}

【候选人素材】
{assets}

【各题型参考题库】（不要照抄，结合 JD 与候选人素材定制；可含追问角度）
{references}

输出 JSON（不要多余文字）：
{{"questions": [{{"qtype": "题型key", "question": "题目", "difficulty": "easy/medium/hard",
 "reference": "评分参考要点（可引自参考题库）"}}]}}

题型配额（每种题型必须出满）：{quota}"""


class _QuestionItem(BaseModel):
    """题单条目 Pydantic 校验"""

    qtype: str
    question: str
    difficulty: str = "medium"
    reference: str = ""
    source: str = "llm"


def _collect_assets_text(db: Session) -> str:
    """简历底稿 + 项目档案 → 题单生成用的素材文本"""
    parts: list[str] = []
    resume = get_resume(db)
    if resume and resume.content:
        parts.append("简历要点：" + json.dumps(resume.content, ensure_ascii=False))
    projects = list_projects(db)
    for p in projects:
        parts.append(
            f"项目《{p.name}》（{p.tech_stack}）：{p.one_liner}；亮点："
            + "；".join(str(h) for h in (p.highlights or []))
        )
    return "\n".join(parts) if parts else "（暂无素材，按通用要求出题）"


def _kb_fill(db: Session, qtype: str, need: int, asked: set[str]) -> list[dict]:
    """配额不足时从题库直接补齐（source=kb）：取检索片段首句作为考点"""
    topic_name = TOPIC_NAMES.get(qtype, qtype)
    items = hybrid_search(topic_name, k=max(need * 3, 6), category="interview")
    filled: list[dict] = []
    for item in items:
        if len(filled) >= need:
            break
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        head = content.split("。", 1)[0][:80]
        question = f"请结合你的理解讲解以下知识点，并举一个工程实践中的例子：{head}"
        if question in asked:
            continue
        asked.add(question)
        filled.append(
            _QuestionItem(
                qtype=qtype,
                question=question,
                difficulty="medium",
                reference=content[:500],
                source="kb",
            ).model_dump()
        )
    return filled


def generate_qlist(
    db: Session, jd_id: int | None = None, quota: dict[str, int] | None = None
) -> QuestionList:
    """生成定制题单：配额检索 → LLM 出题 → Pydantic 校验 → 缺额 kb 补齐 → 落库"""
    quota = {k: int(v) for k, v in (quota or _DEFAULT_QUOTA).items() if int(v) > 0}

    jd_text = "（未关联 JD，按通用岗位要求出题）"
    if jd_id is not None:
        jd = db.get(JdEntry, jd_id)
        if jd is None:
            raise ValueError(f"JD 不存在: id={jd_id}")
        jd_text = f"{jd.title}（{jd.company}）\n{parsed_to_text(jd.parsed)}"

    # 按题型配额检索题库参考（每类取 配额*2 条片段）
    ref_parts: list[str] = []
    for qtype, n in quota.items():
        topic_name = TOPIC_NAMES.get(qtype, qtype)
        ctx = search_as_context(topic_name, k=max(n * 2, 4), category="interview")
        ref_parts.append(f"## {qtype}（{topic_name}）\n{ctx}")
    references = "\n\n".join(ref_parts)

    result = call_llm_json(
        _GEN_PROMPT.format(
            jd=jd_text,
            assets=_collect_assets_text(db),
            references=references[:6000],
            quota=json.dumps(quota, ensure_ascii=False),
        )
    )

    # Pydantic 校验 + 按配额截断
    questions: list[dict] = []
    asked: set[str] = set()
    per_type: dict[str, int] = {k: 0 for k in quota}
    for raw in result.get("questions", []) or []:
        try:
            item = _QuestionItem.model_validate(raw)
        except Exception:
            continue
        if item.qtype not in quota or item.question in asked:
            continue
        if per_type[item.qtype] >= quota[item.qtype]:
            continue
        asked.add(item.question)
        per_type[item.qtype] += 1
        questions.append(item.model_dump())

    # 缺额 kb 补齐（标注 source=kb）
    for qtype, n in quota.items():
        shortfall = n - per_type.get(qtype, 0)
        if shortfall > 0:
            questions.extend(_kb_fill(db, qtype, shortfall, asked))

    qlist = QuestionList(jd_id=jd_id, quota=quota, questions=questions, status="active")
    db.add(qlist)
    db.commit()
    db.refresh(qlist)
    return qlist


def qlist_to_dict(q: QuestionList) -> dict:
    return {
        "id": q.id,
        "jd_id": q.jd_id,
        "quota": q.quota,
        "questions": q.questions,
        "status": q.status,
        "total": len(q.questions or []),
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }
