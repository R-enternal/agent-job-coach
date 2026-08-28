"""项目深挖：从项目库出题 + 生成项目介绍话术"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agent.llm import get_chat_model
from app.rag.search import search_as_context

_DIG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是严苛的技术面试官，专门深挖候选人简历上的项目。"
               "基于项目资料，生成 5 个由浅入深的追问问题，每个问题附参考答案要点。"
               "问题要能检验候选人是否真的做过：实现细节、权衡取舍、踩坑过程、量化结果。"),
    ("human", "项目资料：\n{context}"),
])

_INTRO_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是表达教练。把项目资料改写成面试用介绍话术：先说结论（一句话定位），"
               "再讲为什么（解决的问题），然后讲怎么做（架构与关键实现），最后给量化结果。"
               "口语化、分条、控制在给定时长内能讲完。"),
    ("human", "时长：{minutes}分钟\n\n项目资料：\n{context}"),
])


@tool
def dig_project(project_name: str) -> str:
    """针对指定项目（如 仓维云 / Agent Job Coach）生成 5 个深挖追问及参考答案要点。"""
    context = search_as_context(project_name, k=6, category="project")
    if not context.strip() or context.strip() == "没有找到相关资料。":
        context = search_as_context(project_name, k=6)
    chain = _DIG_PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({"context": context})


@tool
def project_intro(project_name: str, minutes: int = 1) -> str:
    """生成项目面试介绍话术，minutes 支持 0.5 / 1 / 3（分钟）。"""
    context = search_as_context(project_name, k=6, category="project")
    if not context.strip() or context.strip() == "没有找到相关资料。":
        context = search_as_context(project_name, k=6)
    chain = _INTRO_PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({"minutes": minutes, "context": context})
