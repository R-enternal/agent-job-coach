"""知识检索工具：按分类检索知识库并回答（可溯源）"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agent.llm import get_chat_model
from app.rag.search import search_as_context

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是 Agent Job Coach（Agent 求职助手）。基于提供的资料回答用户问题，"
               "答案必须严格来自资料内容，不得编造；资料不足时如实说明。"
               "回答最后标注引用来源。"),
    ("human", "资料：\n{context}\n\n问题：{question}"),
])


@tool
def query_knowledge(question: str, category: str = "") -> str:
    """按知识库分类回答求职相关问题。
    category 可选值：interview(面试题库) / project(项目文档) / resume(个人简历) / jd(岗位JD)，
    留空则全库检索。例如问"RAG 混合检索的原理"应传 interview，问"我的项目亮点"应传 project。
    """
    cat = category or None
    context = search_as_context(question, category=cat)
    chain = _PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({"context": context, "question": question})
