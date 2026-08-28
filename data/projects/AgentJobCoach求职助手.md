# Agent Job Coach · 求职智能助手 项目档案

## 项目定位
面向求职者的 AI 面试陪练与求职知识管理助手：喂入个人简历、项目文档、面试题库、岗位 JD，
实现模拟面试、项目深挖、知识点整理、JD 匹配诊断与面试复盘报告。

## 技术栈
Python FastAPI + MySQL + Redis + Vue3(Element Plus) + LangGraph + Chroma + 智谱 GLM 全家桶（glm-5.1 对话 / glm-4v-plus 识图 / embedding-2 向量）。

## 架构
FastAPI → LangGraph 多智能体 → 工具层 → 分类知识库（向量+BM25+RRF）

### 多智能体
- 问答 Agent：LangGraph ReAct 图（agent 节点 → tools 节点 → 条件边 → 步数上限 6）
- 面试官 Agent：状态机（ask 生成 → wait 独占 interrupt → judge 评分），支持深挖追问
- 报告 Agent：面试复盘 / 项目介绍话术 / JD 匹配报告

### 分类知识库
- 简历库 / 项目库 / 面试题库 / JD 库，元数据 category 过滤检索
- 多格式解析（md/html/pdf/docx）+ 结构感知切块
- 向量(智谱 embedding-2) + BM25 自实现 + RRF 融合，回答带来源引用

### 工具集
- query_knowledge(category)：分类知识检索
- match_job(jd)：JD 技能要求解析 → 与简历匹配度打分
- gen_study_notes(topic)：知识点速查笔记
- dig_project(project)：项目深挖出题 + 回答评判
- gen_review_report()：面试复盘报告

## 记忆
- LangGraph checkpointer（MemorySaver）按 thread_id 隔离
- Redis 会话历史持久化（7 天 TTL）+ 面试状态机
- MySQL 落库：面试记录、评分、学习计划

## 来源
由 ZST 智扫通（扫地机器人客服教学项目）重构而来：手写 ReAct → LangGraph 编排，
场景从产品客服改为求职面试陪练，新增面试状态机与分类知识库。
