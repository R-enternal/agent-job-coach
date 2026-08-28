"""报告生成：面试复盘报告"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agent.llm import get_chat_model

_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是求职教练。根据模拟面试记录生成结构化复盘报告：\n"
               "## 总体评价（含平均分）\n## 各题得分与点评\n"
               "## 暴露的薄弱点（按严重程度排序）\n## 改进计划（具体可执行）\n"
               "## 下次面试前必背清单"),
    ("human", "面试主题：{topic}\n轮次记录：\n{history}"),
])


def generate_review_report(topic: str, rounds: list[dict]) -> str:
    """rounds: [{round, question, answer, score, feedback}]"""
    lines = []
    for r in rounds:
        lines.append(
            f"第{r['round']}题：{r['question']}\n"
            f"我的回答：{r['answer'][:300]}\n"
            f"得分：{r['score']}；点评：{r['feedback']}\n"
        )
    chain = _REVIEW_PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({"topic": topic, "history": "\n".join(lines)})
