"""素材库：简历底稿 + 项目档案（手工录入 / LLM 抽取草稿双轨）"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm import call_llm_json
from app.models import ProjectArchive, ResumeBase
from app.rag.search import search_as_context

_RESUME_PARSE_PROMPT = """你是简历解析器。把简历文本解析为结构化 JSON（不要多余文字）：
{{"education": ["教育经历..."], "skills": ["技能..."], "experiences": ["实习/项目/获奖经历..."]}}

简历文本：
{raw}"""

_PROJECT_EXTRACT_PROMPT = """你是项目档案整理员。根据项目资料，抽取一份项目档案草稿，输出 JSON（不要多余文字）：
{{"name": "项目名", "one_liner": "一句话简介", "tech_stack": "技术栈（| 分隔）",
 "highlights": ["可量化亮点1", "亮点2", "亮点3"],
 "star": {{"situation": "背景/痛点", "task": "你的任务", "action": "关键行动", "result": "量化结果"}}}}

项目资料：
{context}"""


def upsert_resume(db: Session, raw_text: str, version: str = "default") -> ResumeBase:
    """录入/更新简历底稿：LLM 结构化解析（失败不阻断，content 置空由前端手补）"""
    try:
        content = call_llm_json(_RESUME_PARSE_PROMPT.format(raw=raw_text))
    except Exception:
        content = {}
    rec = db.scalars(select(ResumeBase).where(ResumeBase.version == version)).first()
    if rec is None:
        rec = ResumeBase(version=version, raw_text=raw_text, content=content)
        db.add(rec)
    else:
        rec.raw_text = raw_text
        rec.content = content
    db.commit()
    db.refresh(rec)
    return rec


def get_resume(db: Session, version: str = "default") -> ResumeBase | None:
    return db.scalars(select(ResumeBase).where(ResumeBase.version == version)).first()


def create_project(db: Session, payload) -> ProjectArchive:
    rec = ProjectArchive(
        name=payload.name,
        one_liner=payload.one_liner,
        tech_stack=payload.tech_stack,
        highlights=payload.highlights,
        star=payload.star,
        source=payload.source,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_projects(db: Session) -> list[ProjectArchive]:
    return list(
        db.scalars(select(ProjectArchive).order_by(ProjectArchive.updated_at.desc())).all()
    )


def get_project(db: Session, pid: int) -> ProjectArchive | None:
    return db.get(ProjectArchive, pid)


def update_project(db: Session, pid: int, payload) -> ProjectArchive | None:
    rec = db.get(ProjectArchive, pid)
    if rec is None:
        return None
    for field in ("name", "one_liner", "tech_stack", "highlights", "star", "source"):
        value = getattr(payload, field, None)
        if value is not None:
            setattr(rec, field, value)
    db.commit()
    db.refresh(rec)
    return rec


def delete_project(db: Session, pid: int) -> bool:
    rec = db.get(ProjectArchive, pid)
    if rec is None:
        return False
    db.delete(rec)
    db.commit()
    return True


def extract_project_draft() -> dict:
    """从知识库 project 类文档 LLM 抽取项目档案草稿（不落库，前端确认后再 POST）"""
    context = search_as_context("项目经历 技术栈 项目亮点 难点 成果", k=8, category="project")
    if not context.strip() or context.strip() == "没有找到相关资料。":
        return {"error": "知识库 project 分类下没有可用文档，请先上传项目文档"}
    return call_llm_json(_PROJECT_EXTRACT_PROMPT.format(context=context))
