"""LangGraph 状态定义"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class QaState(TypedDict):
    """问答 Agent 状态：消息历史 + 步数计数"""

    messages: Annotated[list[BaseMessage], add_messages]
    step_count: int


class InterviewState(TypedDict):
    """面试官 Agent 状态（human-in-the-loop + 题单化）"""

    topic: str
    round: int                # 题序号（首题 1，下一题 2…）
    asked: list[str]          # 已出题目/追问列表
    scores: list[float]       # 各轮评分累计（含追问轮，兼容用）
    current_question: str     # 当前题目/追问
    answer: str               # 用户当前输入
    last_feedback: str        # 最近一次反馈
    waiting_for: str          # "answer"=等首答 / "followup"=等追问（wait 节点读它）
    need_deep_dive: bool      # judge 后是否要生成追问
    deep_dive_round: int      # 当前题深挖次数（0=首答，上限 2）
    done: bool                # 面试是否结束

    # ---- M2：题单化 ----
    op: str                   # route_op 节点读的指令：answer / pick / skip
    pick_index: int           # pick 目标题下标
    qlist_id: int             # 题单 id（0=非题单模式，走现场生成）
    questions: list[dict]     # 题单快照（start 时从 MySQL 拷入，防中途被改）
    q_idx: int                # 题单游标（下一题下标）
    base_question: str        # 当前题的母题（追问时不变，计分归属用）
    current_reference: str    # 当前题的题单参考要点（judge 优先用，免二次检索）
    cur_first_score: float    # 当前题首答分（-1=未评）
    cur_followup_scores: list[float]  # 当前题追问得分序列
    q_scores: list[dict]      # 每题结算 {round,question,first,followups,final} 或 {skipped:true}
    judge_degraded: bool      # 评分降级显性标记（judge 重试耗尽兜底 5 分）
