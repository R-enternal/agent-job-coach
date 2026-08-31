# Agent Job Coach · AI 面试陪练系统

面向求职者的「个人素材库 + JD 定制」驱动的 AI 面试陪练系统：拍摄 JD 截图即可生成定制题单，
AI 面试官逐题提问、智能追问并实时打分，结束后生成复盘报告，
形成「素材 → 定制 → 陪练 → 复盘」训练闭环。

## 功能总览

| 模块 | 说明 |
|------|------|
| 素材库 | 简历底稿 LLM 结构化解析；项目档案手工录入 / 从知识库 LLM 抽取草稿后确认 |
| JD 定制 | JD 文本粘贴 + **截图上传（glm-4v-plus 多模态识别）**双通道解析，先落 draft，回显编辑确认后才参与题单生成 |
| 题单生成 | 按 JD 要求 + 个人素材 + 题库检索定制出题，配额制（agent/rag/project/八股/hr），LLM 出题不足由题库补齐并标注来源 |
| 模拟面试 | LangGraph 状态机「出题→作答→评分→追问」，支持自由挑题 / 跳过 / 主动结束 / **语音输入**；每题综合分 = 首答 50% + 追问均分 50%；**五维评分**（正确性/深度/结构/表达/风险意识）+ **三档答案打磨**（30s/1min/2min 双语） |
| 知识问答 | SSE 流式对话，Agentic RAG：检索封装为工具由 Agent 自主调用，回答标注引用来源 |
| 复盘对比 | 每场生成复盘报告（含五维归因与表达建议、上场对比）；历史场次点击可回看问答明细（Redis 事件流保留 7 天） |

## 技术栈

Python · FastAPI · LangGraph · Vue3 · Tailwind · MySQL · SQLite · Redis · Chroma · 智谱 GLM 全家桶（glm-5.1 对话 / glm-4v-plus 视觉 / embedding-2 向量）

## 架构

```
Vue3 前端（5174）
  │  /api 代理
  ▼
FastAPI（9902，sync 端点走线程池，不阻塞 SSE）
  ├─ 问答 Agent：ReAct 图，8 类工具（知识检索/JD 匹配/项目深挖/笔记…），步数上限 6
  ├─ 面试官 Agent：状态机 ask→wait(interrupt)→route_op→judge，深挖上限 ≤2 轮代码强制
  │    人机回环：interrupt 独占 wait 节点，resume 负载 op 协议（answer/pick/skip）
  ├─ RAG：多格式解析 + 结构感知切块（标题树/Q&A 边界）+ 向量/BM25 双路召回 RRF 融合
  └─ 评分：response_format=json + Pydantic clamp(0-10) + 失败重试 + 降级兜底 5 分显性标记
存储分层
  ├─ MySQL：持久资产（简历/项目档案/JD/题单/作答/场次）
  ├─ SQLite：LangGraph 图状态 checkpoint（面试图/问答图双库分档，重启断点续答）
  └─ Redis：会话历史 / 面试事件流（7 天 TTL）
```

## 质量保障

- **评分器金标集校准**：12 条人工标注基线（`data/evals/judge_golden.jsonl`），
  通过分档锚点 Prompt 将机器评分与人工基线的一致率（|Δ|≤1 分）从 67% 提升至 **100%**
  （MAE 0.75，Pearson 0.99）。评测脚本：`scripts/eval_judge.py --tag <标签>`，
  逐条明细落盘 `data/evals/judge_eval_result.json`，单变量迭代可追溯。
- **interrupt 重放安全**：LLM/DB 副作用全部位于 wait 之前的节点，resume 只重放幂等的 wait，
  杀进程重启后可按 session_id 断点续答。

## 快速开始

前置：Python 3.11+、Node 18+、MySQL 8、Redis 5+。

```bash
# 1. 后端
cd backend
python -m venv .venv && .venv\Scripts\activate        # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -r requirements.txt                        # 或 uv pip install -r requirements.txt
cp .env.example .env                                   # 填入智谱 API Key 与 MySQL 密码
python scripts/seed_kb.py                              # 首次：灌知识库（题库/项目文档）
python -m uvicorn app.main:app --host 0.0.0.0 --port 9902

# 2. 前端（另开终端）
cd frontend
npm install
npm run dev                                            # http://localhost:5174
```

API 文档：http://127.0.0.1:9902/docs

## 使用流程

1. **素材库**：粘贴简历全文（自动结构化）→ 新增项目档案（或「从知识库抽取草稿」后确认）
2. **JD 定制**：粘贴 JD 文本或上传截图 → 核对解析草稿 →「确认无误」→ 生成定制题单
3. **模拟面试**：按主题现场出题，或选择题单开考；作答 / 挑题 / 跳过，AI 评分并智能追问
4. **复盘**：结束自动生成复盘报告（含上场对比）；面试页「历史场次」点击任意场次可回看问答明细

## 目录结构

```
├── backend/            # FastAPI + LangGraph + RAG
│   ├── app/agent/      # 面试官状态机 / 问答 ReAct / 复盘报告
│   ├── app/api/        # chat / interview / kb / assets / jd / qlist
│   ├── app/rag/        # 解析 / 切块 / 混合检索
│   ├── app/services/   # 素材库 / JD / 题单 / 记忆 / 记录
│   └── scripts/        # seed_kb.py 灌库 / eval_judge.py 评分评测
├── frontend/           # Vue3 + Tailwind（自研组件）
├── data/
│   ├── interview_questions/  # 面试题库
│   ├── projects/             # 项目文档（知识库种子）
│   └── evals/                # 评分金标集与评测结果
└── 运行说明.md
```

## 环境变量

见 `backend/.env.example`。`.env`、简历/JD 原文等个人隐私数据已在 `.gitignore` 中排除。

## 安全提示

本系统面向单人本地使用设计，**无鉴权**：默认 `HOST=0.0.0.0` 时局域网内任何机器均可访问
全部接口（含简历等隐私数据），切勿暴露公网；仅本机使用可在 `.env` 中改 `HOST=127.0.0.1`。
