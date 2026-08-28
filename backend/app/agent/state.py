"""LangGraph 状态定义"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class QaState(TypedDict):
    """问答 Agent 状态：消息历史 + 步数计数"""

    messages: Annotated[list[BaseMessage], add_messages]
    step_count: int


class InterviewState(TypedDict):
    """面试官 Agent 状态（human-in-the-loop）"""

    topic: str
    round: int                # 题序号（首题 1，下一题 2…）
    asked: list[str]          # 已出题目/追问列表
    scores: list[float]       # 各轮评分累计
    current_question: str     # 当前题目/追问
    answer: str               # 用户当前输入
    last_feedback: str        # 最近一次反馈
    waiting_for: str          # "answer"=等首答 / "followup"=等追问（wait 节点读它）
    need_deep_dive: bool      # judge 后是否要生成追问
    deep_dive_round: int      # 当前题深挖次数（0=首答，上限 2）
    done: bool                # 面试是否结束
