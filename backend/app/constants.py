"""公共领域常量（跨模块共享，避免 import 私有名）"""

# 面试题型 key → 中文名（题单配额、面试出题、题库检索共用）
TOPIC_NAMES: dict[str, str] = {
    "agent": "Agent 原理与工程化",
    "rag": "RAG 专项",
    "project": "项目深挖",
    "eight-part": "八股基础",
    "hr": "主管/HR 面",
    "mixed": "综合混面",
}
