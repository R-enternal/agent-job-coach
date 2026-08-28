"""答案打磨 API（M5.5）：三档双语答案 + 表达建议"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import polish

router = APIRouter(prefix="/api/answers", tags=["答案打磨"])


class PolishRequest(BaseModel):
    question: str = Field(description="面试题")
    answer: str = Field(description="候选人原始回答")
    story_id: int | None = Field(default=None, description="可选：引用故事库素材")


@router.post("/polish")
def polish_endpoint(req: PolishRequest, db: Session = Depends(get_db)):
    """原始回答 → 30s/1min/2min 三档双语打磨 + 表达建议"""
    try:
        return polish.polish_answer(db, req.question, req.answer, req.story_id)
    except Exception as exc:
        return {"error": f"打磨失败：{exc}"}
