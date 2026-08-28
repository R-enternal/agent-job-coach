"""ORM 模型：面试记录、答题记录、知识库文档元信息、素材库、JD、题单"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InterviewRecord(Base):
    """一场模拟面试的汇总记录"""

    __tablename__ = "interview_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(64))
    rounds: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[list] = mapped_column(JSON, default=list)  # q_scores 快照：每题 final（跨场次对比用）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AnswerRecord(Base):
    """面试中每道题的作答记录（skipped=True 表示被跳过，不计分但可见）"""

    __tablename__ = "answer_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    round: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    feedback: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class KbDocument(Base):
    """知识库入库记录（含分类）"""

    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # resume/project/interview/jd
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ResumeBase(Base):
    """简历底稿（单用户多版本，version=default 为当前版）"""

    __tablename__ = "resume_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(64), default="default", index=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)  # 结构化：教育/技能/经历
    raw_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class ProjectArchive(Base):
    """项目档案：面试深挖的弹药库（手工录入 / LLM 抽取草稿双轨）"""

    __tablename__ = "project_archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    one_liner: Mapped[str] = mapped_column(String(255), default="")
    tech_stack: Mapped[str] = mapped_column(String(255), default="")
    highlights: Mapped[list] = mapped_column(JSON, default=list)
    star: Mapped[dict] = mapped_column(JSON, default=dict)  # situation/task/action/result
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual / llm_extract
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class JdEntry(Base):
    """岗位 JD 条目：解析结果先落 draft，前端回显编辑后确认（confirmed）"""

    __tablename__ = "jd_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    company: Mapped[str] = mapped_column(String(128), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parsed: Mapped[dict] = mapped_column(JSON, default=dict)  # skills/experience/soft/summary
    source: Mapped[str] = mapped_column(String(16), default="text")  # text / screenshot
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)  # draft / confirmed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class QuestionList(Base):
    """定制题单（M2 状态机消费）：配额 + 题目 + 检索溯源"""

    __tablename__ = "question_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jd_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quota: Mapped[dict] = mapped_column(JSON, default=dict)  # {qtype: count}
    questions: Mapped[list] = mapped_column(JSON, default=list)  # [{qtype,question,difficulty,source,reference}]
    status: Mapped[str] = mapped_column(String(16), default="active")  # active / archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ExperienceStory(Base):
    """STAR 经历故事库（M5.2）：行为面弹药，由口述素材 LLM 整理，人审后使用"""

    __tablename__ = "experience_stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    question: Mapped[str] = mapped_column(String(512), default="")  # 来源行为题
    raw_answer: Mapped[str] = mapped_column(Text, default="")       # 用户口述原文
    star: Mapped[dict] = mapped_column(JSON, default=dict)          # situation/task/action/result
    chinese_version: Mapped[str] = mapped_column(Text, default="")  # 中文面试叙述版
    english_version: Mapped[str] = mapped_column(Text, default="")  # 英文口语版
    language_tips: Mapped[list] = mapped_column(JSON, default=list)  # 表达润色建议
    tags: Mapped[list] = mapped_column(JSON, default=list)          # 能力标签
    can_answer: Mapped[list] = mapped_column(JSON, default=list)    # 可回答的内置行为题
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
