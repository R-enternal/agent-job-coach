"""API 请求/响应模型"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str
    session_id: str = Field(default="default")


class InterviewStartRequest(BaseModel):
    topic: str = Field(default="mixed", description="面试主题：agent / rag / project / eight-part / hr / mixed")
    session_id: str = Field(default="default")
    qlist_id: Optional[int] = Field(default=None, description="题单 id（空=现场生成模式）")


class InterviewAnswerRequest(BaseModel):
    session_id: str
    answer: str


class InterviewPickRequest(BaseModel):
    """自由挑题：跳到题单第 index 题（0 起）"""

    session_id: str
    index: int


class InterviewSkipRequest(BaseModel):
    """跳过当前题：不计分、不计均分、标记 skipped 可见"""

    session_id: str


class InterviewStartResponse(BaseModel):
    session_id: str
    topic: str
    round: int
    question: str
    hint: Optional[str] = None
    progress: Optional[dict] = None  # 题单模式：{"consumed": n, "total": m}


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
    question_score: Optional[float] = None  # 本题综合分（首答50%+追问均分50%），未结算为空
    judge_degraded: bool = False            # 评分降级显性标记
    skipped: bool = False                   # 本次操作是 skip
    progress: Optional[dict] = None         # 题单模式：{"consumed": n, "total": m}（前端进度条）


class KbUploadResponse(BaseModel):
    filename: str
    category: str
    chunks: int


class KbSearchResponse(BaseModel):
    query: str
    items: list[dict]


# ---------- M1：素材库 ----------

class ResumeUpsertRequest(BaseModel):
    raw_text: str = Field(description="简历纯文本")
    version: str = Field(default="default")


class ProjectUpsertRequest(BaseModel):
    name: str
    one_liner: str = ""
    tech_stack: str = ""
    highlights: list[str] = Field(default_factory=list)
    star: dict = Field(default_factory=dict)  # situation/task/action/result
    source: str = "manual"  # manual / llm_extract


# ---------- M1：JD 定制 ----------

class JdParseTextRequest(BaseModel):
    raw_text: str = Field(description="JD 纯文本")


class JdUpdateRequest(BaseModel):
    """回显确认：前端展示 draft 后编辑/确认"""

    title: Optional[str] = None
    company: Optional[str] = None
    raw_text: Optional[str] = None
    parsed: Optional[dict] = None
    status: Optional[str] = Field(default=None, description="draft / confirmed")


# ---------- M1：题单 ----------

class QlistGenerateRequest(BaseModel):
    jd_id: Optional[int] = Field(default=None, description="关联 JD（可空=按通用配额）")
    quota: Optional[dict[str, int]] = Field(
        default=None, description="题型配额，如 {agent:2, rag:2}；空则用默认"
    )
