"""报告生成：面试复盘报告（每题 final 拆解 + 上场对比 + skipped 可见）"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agent.llm import get_chat_model

_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是求职教练。根据模拟面试记录生成结构化复盘报告：\n"
               "## 总体评价（含平均分{prev_hint}）\n## 各题得分与点评\n"
               "## 暴露的薄弱点（按严重程度排序）\n## 改进计划（具体可执行）\n"
               "## 下次面试前必背清单"),
    ("human", "面试主题：{topic}\n轮次记录：\n{history}"),
])


def _fmt_event(e: dict) -> str:
    """单条事件 → 报告行：首答/追问分开列，结算题附 final（首答50%+追问均分50%）"""
    if e.get("skipped"):
        return f"第{e['round']}题：{e['question']}\n【已跳过，未作答不计分】\n"
    line = (
        f"第{e['round']}题：{e['question']}\n"
        f"我的回答：{e['answer'][:300]}\n"
        f"本轮得分：{e['score']}；点评：{e['feedback']}\n"
    )
    if e.get("question_score") is not None:
        line += f"本题综合分：{e['question_score']}（首答50% + 追问均分50%）\n"
    return line


def generate_review_report(
    topic: str, rounds: list[dict], prev_avg: float | None = None
) -> str:
    """rounds: [{round, question, answer, score, feedback, question_score?, skipped?}]
    prev_avg: 同主题上一场平均分（有则报告含对比段）"""
    history = "\n".join(_fmt_event(e) for e in rounds)
    prev_hint = "，并与上一场平均分对比分析进退步" if prev_avg is not None else ""
    if prev_avg is not None:
        history += f"\n\n（参考：同主题上一场平均分为 {prev_avg} 分）"
    chain = _REVIEW_PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({
        "topic": topic,
        "history": history,
        "prev_hint": prev_hint,
    })
