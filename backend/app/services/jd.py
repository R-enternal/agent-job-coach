"""JD 解析：文本（glm-5.1）/ 截图（glm-4v-plus 多模态）→ 先落 draft，PUT 编辑后确认"""

import base64
import json

from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm import call_llm_json, get_vision_model
from app.models import JdEntry

_PARSE_PROMPT = """你是岗位 JD 解析器。从招聘 JD 中提取结构化信息，输出 JSON（不要多余文字）：
{{"title": "岗位名", "company": "公司名（无则空串）",
 "skills": ["技能要求..."], "experience": ["经验要求..."], "soft": ["软实力要求..."],
 "summary": "一句话岗位画像"}}

JD 原文：
{jd}"""

_IMAGE_INSTRUCTION = (
    "请完整识别这张招聘 JD 截图中的文字，并提取结构化信息，输出 JSON（不要多余文字）："
    '{"title": "岗位名", "company": "公司名（无则空串）", '
    '"skills": ["技能要求..."], "experience": ["经验要求..."], "soft": ["软实力要求..."], '
    '"summary": "一句话岗位画像", "raw_text": "截图中识别出的完整原文"}'
)

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def parse_text_jd(db: Session, raw_text: str) -> JdEntry:
    """文本 JD → glm-5.1 结构化解析 → draft 落库（回显确认卖点：先草稿后确认）"""
    parsed = call_llm_json(_PARSE_PROMPT.format(jd=raw_text))
    entry = JdEntry(
        title=str(parsed.pop("title", "") or ""),
        company=str(parsed.pop("company", "") or ""),
        raw_text=raw_text,
        parsed=parsed,
        source="text",
        status="draft",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def parse_image_jd(db: Session, filename: str, data: bytes) -> JdEntry:
    """JD 截图 → glm-4v-plus 多模态识别 + 结构化 → draft 落库"""
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".png"
    mime = _MIME.get(suffix, "image/png")
    b64 = base64.b64encode(data).decode()
    msg = HumanMessage(content=[
        {"type": "text", "text": _IMAGE_INSTRUCTION},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
    ])
    parsed = call_llm_json([msg], llm=get_vision_model())
    raw_text = str(parsed.pop("raw_text", "") or "")
    entry = JdEntry(
        title=str(parsed.pop("title", "") or ""),
        company=str(parsed.pop("company", "") or ""),
        raw_text=raw_text,
        parsed=parsed,
        source="screenshot",
        status="draft",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_jds(db: Session, status: str = "") -> list[JdEntry]:
    stmt = select(JdEntry).order_by(JdEntry.updated_at.desc())
    if status:
        stmt = stmt.where(JdEntry.status == status)
    return list(db.scalars(stmt).all())


def get_jd(db: Session, jid: int) -> JdEntry | None:
    return db.get(JdEntry, jid)


def update_jd(db: Session, jid: int, payload) -> JdEntry | None:
    """回显确认：编辑 title/company/raw_text/parsed，或仅改 status=confirmed"""
    entry = db.get(JdEntry, jid)
    if entry is None:
        return None
    if payload.title is not None:
        entry.title = payload.title
    if payload.company is not None:
        entry.company = payload.company
    if payload.raw_text is not None:
        entry.raw_text = payload.raw_text
    if payload.parsed is not None:
        entry.parsed = payload.parsed
    if payload.status is not None:
        if payload.status not in ("draft", "confirmed"):
            raise ValueError(f"非法 status: {payload.status}")
        entry.status = payload.status
    db.commit()
    db.refresh(entry)
    return entry


def jd_to_dict(entry: JdEntry) -> dict:
    return {
        "id": entry.id,
        "title": entry.title,
        "company": entry.company,
        "raw_text": entry.raw_text,
        "parsed": entry.parsed,
        "source": entry.source,
        "status": entry.status,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def parsed_to_text(parsed: dict) -> str:
    """parsed JSON → 题单生成用的纯文本摘要"""
    return json.dumps(parsed, ensure_ascii=False, indent=2)
