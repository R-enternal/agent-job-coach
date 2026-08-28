"""三档答案打磨（M5.5）：原始回答 → 30s/1min/2min 三档双语答案 + 表达建议

铁律（写进 prompt）：只用候选人原答与故事库素材中的事实，禁止编造数字与经历。
"""

from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.agent.llm import call_llm_json
from app.models import ExperienceStory

_TIERS = ("30s", "1min", "2min")

_POLISH_PROMPT = """你是面试表达教练。基于候选人的原始回答，打磨出三档时长的面试答案（中文 + 英文口语版），并给表达建议。

铁律：只用候选人原答与所附素材中的事实，禁止编造数字与经历；
原答缺失细节时保持留白，在 tips 里提醒候选人补充。

三档口径：
- 30s：电梯陈述，2-3 句，结论先行
- 1min：STAR 简版，背景一句 + 行动两点 + 结果一句
- 2min：完整展开，可含技术细节与量化数据

输出 JSON（不要多余文字）：
{{"versions": {{"30s": {{"zh": "...", "en": "..."}}, "1min": {{"zh": "...", "en": "..."}}, "2min": {{"zh": "...", "en": "..."}}}},
 "tips": ["表达建议 1", "表达建议 2"]}}

面试题：{question}
候选人原始回答：{answer}
{story_block}"""


class _PolishVersion(BaseModel):
    zh: str = ""
    en: str = ""


class _PolishResult(BaseModel):
    """打磨结果校验：档位缺失容忍（前端跳过空档），tips 过滤空串"""

    versions: dict[str, _PolishVersion] = {}
    tips: list[str] = []

    @field_validator("versions", mode="before")
    @classmethod
    def _valid_tiers(cls, v):
        if not isinstance(v, dict):
            return {}
        return {k: v[k] for k in _TIERS if isinstance(v.get(k), dict)}

    @field_validator("tips", mode="before")
    @classmethod
    def _str_list(cls, v):
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if str(x).strip()]


def polish_answer(
    db: Session, question: str, answer: str, story_id: int | None = None
) -> dict:
    """打磨三档双语答案。story_id 命中时注入 STAR 素材。LLM 失败由 API 层转 502。"""
    story_block = ""
    if story_id:
        story = db.get(ExperienceStory, story_id)
        if story is not None:
            story_block = (
                "候选人故事库素材（可引用其中事实）：\n"
                f"《{story.title}》STAR：{story.star}\n叙述：{story.chinese_version}"
            )
    result = _PolishResult.model_validate(call_llm_json(_POLISH_PROMPT.format(
        question=question, answer=answer, story_block=story_block,
    )))
    return {
        "versions": {k: v.model_dump() for k, v in result.versions.items()},
        "tips": result.tips,
    }
