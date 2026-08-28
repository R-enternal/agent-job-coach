# B · 项目 Agent 深挖（精选 13 题）

面试官会顺着你的回答一路追问，⭐=高频。全部基于项目真实实现。

用户提问 → agent 节点（LLM 决策，可能输出文本或 tool_calls）→ 条件边判断 → 有调用进 tools 节点执行 8 类工具 → 结果用 ToolMessage 回填 → 回 agent 节点 → 直到无调用或步数上限 → 总结回答，SSE 流式推前端。


`
flowchart TD
  U["用户提问"] --> A["agent 节点
LLM 决策(bind_tools)"]
  A --> C{"带 tool_calls?"}
  C -- "是" --> T["tools 节点
执行工具"]
  T --> A
  C -- "否" --> S["总结回答"] --> SSE["SSE 流式输出"]
  A -. "步数上限6" .-> S
`

问答是"单轮决策→调工具→总结"的短循环（ReAct 够用）；维保计划是"生成计划→逐步执行→检查再计划"的长任务（Plan-Execute-Replan 合适）。拆开：状态机各自简单、循环独立、可单独测试。

拆的判断标准： ①任务能否拆成不同专长；②是否需要不同上下文；③是否需要独立循环控制和权限。没有明确分工不要硬拆——多 Agent 有协调成本。

_agent_node （LLM 决策）→ _tools_node （执行工具）→ _should_continue （条件边）。终止三层：模型不再要工具、步数上限 6、异常回退（错误回传让模型结束或换路）。


`
flowchart LR
  START["START"] --> A["agent"]
  A --> COND{"有tool_calls 且步数<6?"}
  COND -- "是" --> T["tools"] --> A
  COND -- "否" --> END["END"]
`

正常问答 1~3 步，6 步覆盖复合问题同时控成本。参数校验三层：模型 schema 约束 → 参数默认值兜底 → try/except 失败回传让模型修正重试。

先理解"工具调用是成对出现的"： 模型调用工具时，消息像"下单 + 收货"一样配对：


`
第1条 user:  电机过热怎么排查？
第2条 ai:    （我要调用 retrieve_knowledge，编号 id=call_1）
第3条 tool:  （call_1 的结果）手册内容：先检查散热风扇…
第4条 ai:    根据手册，第一步检查散热风扇…
`

第 2 条说"我要调 call_1"，第 3 条拿着 call_1 的结果回来。**API 要求这个配对必须完整**——有"下单"就必须有"收货"。

什么是孤儿调用： 只有下单、没有收货——第 2 条之后连接断了，工具结果没写进历史。这条"断腿"的 AI 消息就是孤儿调用。

为什么整个会话废掉： 脏数据存在会话历史里（Redis 7 天 TTL），下次请求会把整个历史发给 DeepSeek，API 一查 call_1 有调用没结果 → 配对不完整 → 直接 400。每次请求都带这段脏历史，所以每次都失败——**重启没用，得清掉脏数据**。

解决（自愈清洗） ：每次调 LLM 前执行 _sanitize_messages ：①只留一条系统消息；②有调用但后面没结果的 → 删调用、保留它说的正文；③有结果但前面没调用的 → 丢弃；④删空占位。

为什么不会误删正常消息： 判断标准是"这条调用的编号后面是否真的出现了对应结果"——有结果的一律保留，只有真断腿的才处理（"先剔除再配对"）。

为什么是好素材： 这个问题光会调 API 发现不了——必须理解 function calling 的消息配对机制（tool_call_id ↔ ToolMessage）才能定位，证明你懂机制而不是调接口的。


`
flowchart TD
  HIST["会话历史"] --> S1["保留1条SystemMessage"]
  S1 --> S2{"AI带tool_calls?"}
  S2 -- "是" --> S3{"后续有对应ToolMessage?"}
  S3 -- "有" --> KEEP["保留"]
  S3 -- "没有" --> FIX["剔调用保正文"]
  S2 -- "否" --> S4{"孤立ToolMessage?"}
  S4 -- "是" --> DROP["丢弃"]
  S4 -- "否" --> KEEP
  KEEP --> OUT["发给LLM"]; FIX --> OUT; DROP --> OUT
`

- 问答准确率 35%→100% ：从手册出 20 题（答案可溯源），裸答 35%、接 RAG 后 100%，判定=关键短语命中+人工抽查；

- 召回 recall@1 50%→65%、recall@2 50%→100% ：结构感知切块 + 向量/BM25 混合检索后的实测；

- 故障检出 15/15、平均提前 17.6 分钟、误报率 0.4% ：30 设备日模拟数据 + 15 个故障注入场景。

口径要点： 主动说"20 题小规模评测集、答案可溯源"，比藏着更可信。

记忆分三层：

- 工作记忆 ：当前任务执行状态（调了哪些工具、执行到哪步）——LangGraph checkpoint（MemorySaver），按 thread_id 隔离；

- 短期记忆 ：本次会话多轮消息——Redis JSON 持久化（7 天 TTL），解决切页面/重启丢对话；

- 长期记忆 ：设备档案、维保历史、用户画像——落 MySQL 业务表，需要时按需查，不塞上下文。

对话记忆实现链路： MemorySaver 存图内状态 → 每轮结束 save_session_history 把消息序列化成 JSON rpush 写 agent:history:{session_id} （覆盖写+7 天 TTL）→ 读取优先 Redis、兜底 MemorySaver → 清空会话时 delete_thread + redis.delete 两层一起清。

选型过程（真实）： LangGraph 官方 RedisSaver 依赖 Redis 的 RediSearch 模块 ，本机没有，所以用 redis-py 自实现。取舍：自实现存的是"对话内容"而非完整图状态——问答场景够用，也说明理解两种方案的差异。

记忆边界： 7 天 TTL 防膨胀；不把全部历史塞 prompt（RAG 只带 top-4）；脏记忆（孤儿消息）进上下文前先清洗；长期记忆按需召回。

局限： MemorySaver 是进程内存，多实例部署不共享——生产换 RedisSaver/PostgresSaver 外部存储；语义记忆（向量检索历史）和自动摘要压缩是规划项。

astream(stream_mode=["messages","updates"]) ：messages 出 token，updates 出工具事件，前端能看到"正在调哪个工具"。传输用 SSE（服务端单向推送、自动重连）；WebSocket 适合双向实时，这里不需要。

规则降级模型（RuleBasedChatModel）：关键词路由→调工具→总结，离线跑通全链路。多模型全走 OpenAI 兼容接口（base_url/model/key 可配），DeepSeek 对话 + GLM embedding，切模型只改配置。

不会：session_id 作 thread_id 隔离 MemorySaver，Redis key 也按 session 隔离。局限：MemorySaver 是进程内存，多实例部署要换外部存储（RedisSaver/PostgresSaver）。

planner（生成步骤计划）→ executor（逐步执行，记录 past_steps）→ replanner（检查：有最终报告则 END，否则重新计划）。适合"执行中发现新情况要调整"的长任务。


`
flowchart LR
  START["任务"] --> P["planner"]
  P --> E["executor"]
  E --> R["replanner"]
  R --> C{"有response?"}
  C -- "否" --> P
  C -- "是" --> END["报告"]
`

数据链路检测（超时未上报）+ 数据质量检测（恒值/跳变/超量程）识别传感器自身异常，触发独立 DATA_LINK 告警，并把异常点位从健康度计算中隔离——避免"传感器坏了误判成设备坏了"。

记忆层换外部存储、鉴权限流审计、工具权限分级（写操作审批）、链路 trace、评测流水线化、模型多路降级熔断、知识库版本管理 + 向量库升级。
