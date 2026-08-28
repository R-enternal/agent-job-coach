"""API 请求/响应模型"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str
    session_id: str = Field(default="default")


class InterviewStartRequest(BaseModel):
    topic: str = Field(description="面试主题：agent / rag / project / eight-part / hr / mixed")
    session_id: str = Field(default="default")


class InterviewAnswerRequest(BaseModel):
    session_id: str
    answer: str


class InterviewStartResponse(BaseModel):
    session_id: str
    topic: str
    round: int
    question: str
    hint: Optional[str] = None


class InterviewAnswerResponse(BaseModel):
    session_id: str
    round: int
    question: str
    score: float
    feedback: str
    next_question: Optional[str] = None
    next_type: Optional[str] = None  # "question"=下一题 / "followup"=深挖追问
    finished: bool = False
    summary: Optional[str] = None


class KbUploadResponse(BaseModel):
    filename: str
    category: str
    chunks: int


class KbSearchResponse(BaseModel):
    query: str
    items: list[dict]
