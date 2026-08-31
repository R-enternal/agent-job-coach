"""答案打磨 API（M5.5）：三档双语答案 + 表达建议"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import polish

router = APIRouter(prefix="/api/answers", tags=["答案打磨"])


class PolishRequest(BaseModel):
    question: str = Field(description="面试题")
    answer: str = Field(description="候选人原始回答")


@router.post("/polish")
def polish_endpoint(req: PolishRequest):
    """原始回答 → 30s/1min/2min 三档双语打磨 + 表达建议"""
    try:
        return polish.polish_answer(req.question, req.answer)
    except Exception as exc:
        return {"error": f"打磨失败：{exc}"}
