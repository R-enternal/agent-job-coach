"""报告生成：面试复盘报告（每题 final 拆解 + 上场对比 + skipped 可见）"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agent.llm import get_chat_model

_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是求职教练。根据模拟面试记录生成结构化复盘报告（所有得分满分均为 10 分）：\n"
               "## 总体评价（含平均分{prev_hint}）\n## 各题得分与点评（结合五维指出亮点/短板）\n"
               "## 暴露的薄弱点（按严重程度排序，按五维低分维度归因）\n## 改进计划（具体可执行）\n"
               "## 表达建议（2-4 条，聚焦表达而非知识点，不与各题点评重复；"
               "每条格式：【原句】摘录候选人原话 → 【改进】更有说服力的说法 → "
               "【理由】为什么更好；关注表达结构、量化意识、术语准确性）\n"
               "## 下次面试前必背清单"),
    ("human", "面试主题：{topic}\n轮次记录：\n{history}"),
])

_DIM_LABELS = {
    "correctness": "正确性",
    "depth": "深度",
    "structure": "结构",
    "expression": "表达",
    "risk_awareness": "风险意识",
}


def _fmt_event(e: dict) -> str:
    """单条事件 → 报告行：首答/追问分开列，结算题附 final（首答50%+追问均分50%），有五维则列出"""
    if e.get("skipped"):
        return f"第{e['round']}题：{e['question']}\n【已跳过，未作答不计分】\n"
    line = (
        f"第{e['round']}题：{e['question']}\n"
        f"我的回答：{e['answer'][:300]}\n"
        f"本轮得分：{e['score']}；点评：{e['feedback']}\n"
    )
    dims = e.get("dims") or {}
    if dims:
        line += "五维：" + " / ".join(
            f"{_DIM_LABELS.get(k, k)} {v}" for k, v in dims.items()
        ) + "\n"
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
