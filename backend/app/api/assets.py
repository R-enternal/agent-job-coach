"""素材库 API：简历底稿 + 项目档案（手工 / LLM 抽取草稿）"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ProjectUpsertRequest, ResumeUpsertRequest
from app.services import assets

router = APIRouter(prefix="/api/assets", tags=["素材库"])


def _resume_to_dict(rec) -> dict:
    return {
        "id": rec.id,
        "version": rec.version,
        "content": rec.content,
        "raw_text": rec.raw_text,
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
    }


def _project_to_dict(rec) -> dict:
    return {
        "id": rec.id,
        "name": rec.name,
        "one_liner": rec.one_liner,
        "tech_stack": rec.tech_stack,
        "highlights": rec.highlights,
        "star": rec.star,
        "source": rec.source,
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
    }


@router.post("/resume")
def upsert_resume(req: ResumeUpsertRequest, db: Session = Depends(get_db)):
    """录入/更新简历底稿（LLM 结构化解析，失败不阻断）"""
    return _resume_to_dict(assets.upsert_resume(db, req.raw_text, req.version))


@router.get("/resume")
def get_resume(version: str = "default", db: Session = Depends(get_db)):
    rec = assets.get_resume(db, version)
    return _resume_to_dict(rec) if rec else {"error": "尚未录入简历底稿"}


@router.post("/projects")
def create_project(req: ProjectUpsertRequest, db: Session = Depends(get_db)):
    """手工新增项目档案（或前端确认 LLM 草稿后提交，source=llm_extract）"""
    return _project_to_dict(assets.create_project(db, req))


@router.post("/projects/extract")
def extract_project():
    """从知识库 project 类文档 LLM 抽取档案草稿（不落库，前端回显确认后再 POST /projects）"""
    return assets.extract_project_draft()


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    return {"items": [_project_to_dict(p) for p in assets.list_projects(db)]}


@router.put("/projects/{pid}")
def update_project(pid: int, req: ProjectUpsertRequest, db: Session = Depends(get_db)):
    rec = assets.update_project(db, pid, req)
    return _project_to_dict(rec) if rec else {"error": f"项目不存在: id={pid}"}


@router.delete("/projects/{pid}")
def delete_project(pid: int, db: Session = Depends(get_db)):
    return {"deleted": assets.delete_project(db, pid)}
