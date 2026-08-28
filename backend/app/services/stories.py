"""STAR 经历故事库（M5.2）：口述素材 → LLM 整理为 STAR 双语故事 → 落库

铁律（写进 prompt）：只用用户提供的素材，禁止编造事实、禁止虚构数字；
缺失细节留空并在 language_tips 提醒用户补充。
"""

from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm import call_llm_json
from app.models import ExperienceStory

# 内置 10 道高频行为题（中英 + 作答提示），GET /api/stories/questions 用
BEHAVIORAL_QUESTIONS: list[dict] = [
    {"id": 1, "zh": "请做一个自我介绍", "en": "Tell me about yourself.",
     "tip": "60-90 秒：背景一句话 → 核心项目 → 为什么适合这个岗位"},
    {"id": 2, "zh": "讲一个你印象最深的技术挑战，你是怎么解决的", "en": "Describe a technical challenge you overcame.",
     "tip": "STAR 结构；挑战要具体，行动要体现你的判断而非运气"},
    {"id": 3, "zh": "讲一次失败或搞砸的经历", "en": "Tell me about a time you failed.",
     "tip": "重点是复盘与改进闭环，不要选伤及团队信任的失败"},
    {"id": 4, "zh": "讲一次和队友意见冲突的经历", "en": "Tell me about a conflict with a teammate.",
     "tip": "聚焦'如何用事实和数据对齐'，不要贬低对方"},
    {"id": 5, "zh": "讲一次 deadline 压力下交付的经历", "en": "Tell me about delivering under a tight deadline.",
     "tip": "体现优先级取舍（砍什么保什么）与风险管理"},
    {"id": 6, "zh": "讲一件你主动推动、超出职责范围的事", "en": "Tell me about a time you showed initiative.",
     "tip": "体现 ownership：发现问题 → 自发行动 → 量化结果"},
    {"id": 7, "zh": "讲一次快速学习新技术的经历", "en": "Tell me about learning a new technology quickly.",
     "tip": "说清学习方法（文档/源码/最小实践）与产出"},
    {"id": 8, "zh": "为什么选择这个方向 / 我们公司", "en": "Why this field / our company?",
     "tip": "结合岗位 JD 与你的真实项目经历，忌空话"},
    {"id": 9, "zh": "你的职业规划是什么", "en": "What is your career plan?",
     "tip": "1 年落地 + 3 年方向，与应聘岗位成长路径对齐"},
    {"id": 10, "zh": "你的优点和缺点是什么", "en": "What are your strengths and weaknesses?",
     "tip": "缺点要真实 + 已在改进；避免'我太追求完美'式假缺点"},
]

_QUESTIONS_TEXT = "\n".join(f"{q['id']}. {q['zh']}（{q['en']}）" for q in BEHAVIORAL_QUESTIONS)

_STORY_PROMPT = """你是求职故事教练。根据候选人的真实经历口述，整理成 STAR 结构的行为面试故事。

铁律：只允许使用候选人提供的素材，禁止编造事实、禁止虚构数字、禁止夸大角色；
口述中缺失的细节在对应字段留空，并在 language_tips 里提醒候选人补充。

输出 JSON（不要多余文字）：
{{"title": "故事标题（10 字内）",
 "star": {{"situation": "背景/痛点", "task": "你的任务", "action": "关键行动", "result": "量化结果"}},
 "chinese_version": "中文面试叙述版（2 分钟口径，口语化，先说结论）",
 "english_version": "英文口语版（自然简洁，适合说出口，不要逐字翻译腔）",
 "language_tips": ["表达改进建议 1", "建议 2"],
 "tags": ["能力标签，如 抗压/团队协作/ownership/学习能力"],
 "can_answer": [这个故事能回答的内置题号列表，从下方题目中选 1-4 个]}}

内置行为题列表：
{questions}

来源行为题：{question}
候选人口述：{raw_answer}"""


class _StoryDraft(BaseModel):
    """LLM 故事草稿的 Pydantic 校验：字段兜底为空，can_answer 只保留合法题号"""

    title: str = ""
    star: dict = {}
    chinese_version: str = ""
    english_version: str = ""
    language_tips: list[str] = []
    tags: list[str] = []
    can_answer: list[int] = []

    @field_validator("can_answer", mode="before")
    @classmethod
    def _valid_ids(cls, v):
        if not isinstance(v, list):
            return []
        valid = {q["id"] for q in BEHAVIORAL_QUESTIONS}
        out = []
        for x in v:
            try:
                i = int(x)
            except (TypeError, ValueError):
                continue
            if i in valid:
                out.append(i)
        return out

    @field_validator("language_tips", "tags", mode="before")
    @classmethod
    def _str_list(cls, v):
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if str(x).strip()]


def story_to_dict(s: ExperienceStory) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "question": s.question,
        "raw_answer": s.raw_answer,
        "star": s.star,
        "chinese_version": s.chinese_version,
        "english_version": s.english_version,
        "language_tips": s.language_tips,
        "tags": s.tags,
        "can_answer": s.can_answer,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def generate_story(db: Session, question: str, raw_answer: str) -> ExperienceStory:
    """口述素材 → LLM 生成 STAR 双语故事 → 落库。LLM 失败抛异常由 API 层转 502。"""
    draft = _StoryDraft.model_validate(call_llm_json(_STORY_PROMPT.format(
        questions=_QUESTIONS_TEXT, question=question, raw_answer=raw_answer,
    )))
    rec = ExperienceStory(
        title=draft.title or question[:20],
        question=question,
        raw_answer=raw_answer,
        star=draft.star,
        chinese_version=draft.chinese_version,
        english_version=draft.english_version,
        language_tips=draft.language_tips,
        tags=draft.tags,
        can_answer=draft.can_answer,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_stories(db: Session) -> list[ExperienceStory]:
    return list(db.scalars(
        select(ExperienceStory).order_by(ExperienceStory.created_at.desc())
    ).all())


def delete_story(db: Session, sid: int) -> bool:
    rec = db.get(ExperienceStory, sid)
    if rec is None:
        return False
    db.delete(rec)
    db.commit()
    return True
