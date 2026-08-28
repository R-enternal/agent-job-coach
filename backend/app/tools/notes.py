"""知识点整理：按主题检索题库并生成结构化速查笔记"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agent.llm import get_chat_model
from app.rag.search import search_as_context

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是面试知识整理专家。根据资料生成结构化速查笔记，格式：\n"
               "## 一句话定义\n## 核心原理\n## 面试问法（至少3个）\n"
               "## 必背要点（编号列表）\n## 易错点"),
    ("human", "主题：{topic}\n\n参考资料：\n{context}"),
])


@tool
def gen_study_notes(topic: str) -> str:
    """根据主题（如 RAG、LangGraph、function calling）生成结构化面试速查笔记。"""
    context = search_as_context(topic, k=5, category="interview")
    if not context.strip() or context.strip() == "没有找到相关资料。":
        context = search_as_context(topic, k=5)
    chain = _PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({"topic": topic, "context": context})
