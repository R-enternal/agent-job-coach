"""STAR 经历故事库 API（M5.2）：生成 / 列表 / 删除 / 内置行为题"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import stories

router = APIRouter(prefix="/api/stories", tags=["经历故事"])


class StoryGenerateRequest(BaseModel):
    question: str = Field(description="来源行为题")
    raw_answer: str = Field(description="用户口述的经历素材")


@router.post("")
def generate(req: StoryGenerateRequest, db: Session = Depends(get_db)):
    """口述素材 → LLM 整理 STAR 双语故事并落库"""
    try:
        rec = stories.generate_story(db, req.question, req.raw_answer)
    except Exception as exc:
        return {"error": f"故事生成失败：{exc}"}
    return stories.story_to_dict(rec)


@router.get("")
def story_list(db: Session = Depends(get_db)):
    return {"items": [stories.story_to_dict(s) for s in stories.list_stories(db)]}


@router.delete("/{sid}")
def remove(sid: int, db: Session = Depends(get_db)):
    return {"deleted": stories.delete_story(db, sid)}


@router.get("/questions")
def questions():
    """内置 10 道高频行为题（中英 + 作答提示）"""
    return {"items": stories.BEHAVIORAL_QUESTIONS}
