# HealthPDF Agent 技术报告模板

## 1. 项目名称

HealthPDF Agent：面向大健康教材的多 Agent Hybrid PDF-RAG 问答系统

## 2. 200 字以内摘要

HealthPDF Agent 是一个基于 Python + Gradio 的医学教材问答系统。项目通过 Router / Query Planner Agent 理解用户意图，使用 PDF Search Agent 对本地教材进行 Embedding + TF-IDF 混合检索，并由 Answer Agent 生成带文件名和页码引用的结构化回答。系统支持无 key、无教材、无索引情况下正常启动，并保留医学安全边界，适合黑客松演示和 ModelScope 创空间部署。

## 3. 问题背景

医学教材内容专业、篇幅长，用户在学习时往往难以快速定位相关知识点。传统关键词搜索难以覆盖同义表达，单纯大模型回答又缺乏可追溯依据。因此，本项目尝试将本地教材检索和大模型回答结合，提升医学学习问答的可解释性。

## 4. 目标用户

- 医学、生命科学和大健康方向学生
- 黑客松评审和演示用户
- 需要快速查阅本地医学教材的学习者

## 5. 核心功能

- 本地 PDF 按页解析和 chunk 切分
- TF-IDF 本地关键词索引
- 远程 Embedding 语义索引
- Hybrid 检索、合并去重和命中方式展示
- Router / Query Planner 意图判断
- 症状类问题的安抚、非诊断性解释和安全提示
- Gradio 聊天页面、索引构建、索引检查和上传 PDF 临时索引

## 6. 系统架构

- 前端层：`app.py`，负责聊天、索引按钮、上传 PDF、状态卡片和检索片段展示。
- Pipeline 层：`src/rag_pipeline.py`，统一编排查询规划、检索和回答。
- Agent 层：`src/agents.py`，包含 Router / Query Planner Agent、PDF Search Agent、Answer Agent。
- 检索层：`src/vector_store.py`，管理 TF-IDF、embedding matrix、metadata 和 hybrid search。
- 数据层：`src/pdf_loader.py`、`src/chunker.py`。
- 模型层：`src/llm_client.py`、`src/embedding_client.py`。

## 7. 多 Agent 流程

1. 用户输入问题。
2. Router / Query Planner Agent 判断 intent。
3. 问候类问题直接回复，不检索 PDF。
4. 医学学习问题生成关键词和 expanded_query。
5. 症状类问题生成检索任务，同时要求 Answer Agent 安抚用户、避免诊断、提示补充信息和必要时就医。
6. PDF Search Agent 根据计划执行 hybrid 检索。
7. Answer Agent 基于检索片段和 Query Plan 输出结构化回答。

## 8. Hybrid RAG 检索设计

系统同时执行：

- original_query 的 embedding 检索
- expanded_query 的 embedding 检索
- original_query、expanded_query 和 keywords 的 TF-IDF 检索

结果按 `source_file + page + chunk_id` 去重，并保留 `match_type`，例如 `embedding_original`、`embedding_expanded`、`tfidf_keywords`。

## 9. Embedding 缓存设计

构建索引时，系统调用 OpenAI-compatible embeddings API，将每个 chunk 的向量保存到 `indexes/healthpdf_index.pkl`。缓存 metadata 包含构建时间、PDF 文件列表、chunk 数量、chunk 参数、后端类型、embedding 模型和索引可用性。

## 10. TF-IDF fallback 设计

如果 embedding API 未配置、调用失败或返回异常，系统不会中断构建流程，而是保留 TF-IDF 索引继续运行。查询时如果 embedding 检索不可用，也会自动使用 TF-IDF。

## 11. 前端交互设计

前端采用浅色蓝绿色大健康风格，包括：

- 顶部项目说明和安全提示
- 左侧 API、教材、索引状态卡片
- 构建索引、检查索引、debug 模式、上传 PDF 控件
- 中间多轮聊天区
- 右侧 Agent 路由信息和教材片段展示

## 12. 部署方式

项目入口为 `app.py`，支持 `PORT` 和 `GRADIO_SHARE` 环境变量。可本地运行，也可部署到 ModelScope 创空间。部署时需要在平台配置 API 环境变量；教材 PDF 可在部署环境上传或通过页面临时上传构建索引。

## 13. 医学安全边界

系统仅用于学习与信息辅助理解，不能替代医生诊断和治疗建议。症状类问题不输出确定性诊断，不给出替代临床决策的治疗方案，并提示必要时就医。

## 14. 当前不足

- Embedding 依赖远程 API，速度和稳定性受网络和模型服务影响。
- 扫描版 PDF 如果没有 OCR 文本，检索效果有限。
- Query Planner 有规则兜底，但仍可能受 LLM 输出质量影响。
- 当前未实现用户权限、日志审计和医学风险分级。

## 15. 后续优化方向

- 增加 OCR 处理扫描版 PDF。
- 增加检索重排序和引用一致性校验。
- 支持按教材、章节、页码范围筛选。
- 加入医学术语高亮和可视化知识卡片。
- 增加更严格的症状风险分级和紧急情况提示。

## 16. GitHub 链接占位

GitHub：待填写

## 17. 部署链接占位

在线演示：待填写
