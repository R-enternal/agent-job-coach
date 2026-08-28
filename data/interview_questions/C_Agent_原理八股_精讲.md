# C · Agent 原理八股（精讲）

原理题考"你真懂还是只会调库"，每题能讲 1~2 分钟。

关系： LangGraph 从 LangChain 生态拆出的独立项目，互补不是竞争—— LangChain 提供"积木"，LangGraph 提供"搭积木的流程控制" 。

LangChain 的用处（组件化工具集）： 模型接入（ChatOpenAI 统一接口）、Prompt/消息结构、RAG 全家桶（切块/embedding/Chroma）、@tool 工具封装。适合 管道式任务 ：加载→切块→向量化→检索→生成。

LangGraph 的用处（工作流引擎）： StateGraph 状态机：节点、边、条件边、checkpointer。解决 有循环、有条件分支、需要中断恢复和审计 的场景：ReAct、Plan-Execute-Replan、多智能体、流式输出。

项目分工： RAG 用 LangChain 组件，Agent 编排用 LangGraph；特意没用老版 AgentExecutor（黑盒循环难审计）。

ReAct ：Thought → Action → Observation 循环，Observation 来自真实工具返回而非模型编造，能纠错、能查新信息。适合短循环问答。

Plan-Execute-Replan ：先规划完整步骤 → 逐步执行 → 检查结果重新规划。适合多步长任务。

一句话： ReAct 是"走一步看一步"，Plan-Execute-Replan 是"先看全图再走路，走歪了回来重看全图"。

请求时把工具列表（name/description/parameters JSON Schema）传给模型，模型在训练中学会输出结构化 tool_calls；服务端执行后把结果作为新消息回传。

写 tool 四要点： ①函数名=工具名，语义直白；②docstring 是给模型的说明书，写清"何时用、输入输出"；③参数类型+默认值兜底；④返回格式化字符串、控制长度。项目 8 工具统一注册进 ALL_AGENT_TOOLS 再 bind_tools。


`
sequenceDiagram
  participant APP as 应用
  participant LLM as LLM
  APP->>LLM: 问题 + 工具Schema
  LLM-->>APP: tool_calls{name,args,id}
  APP->>APP: 执行工具
  APP->>LLM: ToolMessage回填
  LLM-->>APP: 最终回答
`

RAG=外挂知识、更新快、可溯源、成本低（本项目场景）；微调=改行为/风格、更新慢、成本高；长上下文=简单但贵、且超长会注意力稀释。知识频繁更新→RAG；固定行为→微调；材料小且一次性→长上下文。

Orchestrator-Worker（主从拆任务，最常用）、Pipeline（流水线）、Debate（互评，质量高成本高）、Hierarchical（层级管理）。项目当前是"双智能体+图内多节点"的轻量协作。

MCP 是 标准化工具/数据接入协议 （"Agent 的 USB 接口"）：Host（宿主）→ Client（连接器）→ Server（暴露 tools/resources/prompts）→ Transport（stdio/HTTP）。一次接入处处复用，统一权限审计。

区别： function calling 是"单个模型↔应用内工具"的机制；MCP 是生态级标准。一句话： function calling 是地基，MCP 是把它标准化、可插拔的上层协议。

Skill = "说明书式能力包"：一个 SKILL.md（何时用、怎么做）+ 脚本/参考文件。 核心是按需加载 ——任务匹配时模型才去读说明书执行，不占上下文、可插拔、更新不动模型。

插件 = Skill 的打包分发形式（plugin.json 元数据 + SKILL.md + 命令）。 三者的分工： MCP 管"能调什么外部能力"，Skill 管"任务怎么做"，插件管"怎么分发安装"。

触发：消息轮数/总 token 超预算。压缩方式：LLM 把旧消息摘成结构化要点（保留关键结论、数值、待办）。防丢信息：区分"可丢弃的细节"（寒暄/过程）和"必须保留的事实"（数值/结论），关键事实同时落到数据库/记忆层，不只靠上下文。记忆分层见 B7 详解。

提示注入（系统指令强约束+外部内容隔离+工具白名单）、权限最小化（只读直接执行，写操作审批）、沙箱（代码类工具隔离+超时熔断）、输出审计（敏感脱敏+全量日志可追溯）。

SSE 是单向（服务端→客户端）HTTP 长连接，自带重连、实现简单，适合持续推送（LLM token 流）——流式生成用它；WebSocket 双向全双工，适合聊天室/协同编辑。防死循环见 E2 详解。
