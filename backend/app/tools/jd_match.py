"""JD 匹配度诊断：解析 JD 技能要求 → 与简历/项目对比 → 输出匹配报告"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agent.llm import get_chat_model
from app.rag.search import search_as_context

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是资深求职顾问。基于岗位 JD 和个人资料，输出结构化匹配度诊断报告：\n"
               "1. JD 技能要求清单（技术/经验/软实力）\n"
               "2. 匹配度打分（0-100）\n"
               "3. 强项（有证据支撑）\n"
               "4. 差距与风险\n"
               "5. 简历优化建议"),
    ("human", "岗位JD：\n{jd}\n\n个人资料：\n{context}"),
])


@tool
def match_job(jd_text: str) -> str:
    """根据岗位 JD 文本与个人简历/项目经历做匹配度诊断，输出打分与优化建议。"""
    context = search_as_context(jd_text, k=6, category=None)
    chain = _PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({"jd": jd_text, "context": context})
