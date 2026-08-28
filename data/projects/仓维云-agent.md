# 仓维云（仓脉智诊）项目档案

## 项目定位
面向中小仓储企业的轻量化 AI 设备智能维检 SaaS（商界精英挑战赛作品）。独立负责软件层：后端/算法/Agent/双端界面。

## 技术栈
Python FastAPI + MySQL + Redis + Vue3 + ECharts + uni-app 小程序 + LangGraph + Chroma + GLM(embedding)/DeepSeek(对话)。

## 核心能力
### 1. 五引擎诊断
- 阈值告警：连续 3 次防抖
- 趋势告警：滑动窗口 + 线性回归
- 孤立森林：正常数据 >=100 条训练，异常分作为健康度辅助信号、不直接告警
- Holt 预测：horizon=12，输出 ETA
- 融合诊断：轴承磨损/电机过热/负载异常/复合故障

### 2. 健康度算法
健康度 = 100 − 扣分（阈值30/50、趋势20、预测10、稳定性≤15、异常≤15）
权重：振动 0.6 / 温度 0.3 / 电流 0.1
分级：≥90 健康 / 70~89 亚健康 / <70 异常

### 3. Agent（LangGraph 双智能体）
- 对话 Agent：ReAct 循环，8 类工具，步数上限 6，temperature=0
- 维保计划 Agent：Plan-Execute-Replan（planner → executor → replanner）
- Redis + MemorySaver 双层记忆（7 天 TTL）
- 流式 SSE（messages 出 token、updates 出工具事件）
- 孤儿 tool_calls 自愈清洗（_sanitize_messages）
- 无 Key 规则降级模型（RuleBasedChatModel 离线可跑）

### 4. RAG 知识库
- 多格式解析：md/txt/html/pdf/docx/json/csv/xlsx，PDF 带页码 + 表格
- 结构感知切块：标题树 / 中文分隔符（段落>句子>逗号）
- 向量/BM25 混合检索 RRF 融合，GLM embedding + Chroma top-4
- 检索结果可溯源（来源/章节/页码）

## 实测数据（面试必背）
- 问答准确率 35%→100%（20 题评测集，答案可溯源）
- 召回 recall@1 50→65% / recall@2 50→100%
- 故障检出 15/15、预测平均提前 17.6 分钟、误报率 0.4%

## 开发故事
商业计划书拆需求 → 定技术栈（后端选 Python 因为 Agent 一定用 Python）→ 先读参考项目 → 基础功能逐域开发（设备/监测/告警/工单/备件/资产）→ 算法迭代成五引擎 → 双 Agent 协作开发（Claude 写代码 + Codex 审查，quality-gate 通行证前不合并）→ 量化评测收尾。

## 工程亮点
- 告警优先级：预测(扣10) < 趋势(扣20) < 阈值(扣30/50)，越早的预警扣分越轻
- 记忆三层：工作记忆（checkpoint）/ 短期记忆（Redis 7天TTL）/ 长期记忆（MySQL 按需查）
- 数据链路检测 + 数据质量检测（恒值/跳变/超量程），传感器异常独立 DATA_LINK 告警并隔离
