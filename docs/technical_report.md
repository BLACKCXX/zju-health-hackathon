# HealthPDF Agent 技术报告

## 1. 项目名称

HealthPDF Agent

## 2. 项目摘要

HealthPDF Agent 是一个面向大健康教材问答的多 Agent PDF-RAG 系统。项目采用 Vue + Ant Design Vue + ECharts 前端和 FastAPI 后端，复用本地 PDF 检索、Hybrid RAG、Router / Query Planner Agent、PDF Search Agent 与 Answer Agent，生成带教材引用的结构化回答，并保留医学安全边界。

## 3. 问题背景

医学教材专业性强、篇幅长，学习者很难快速定位相关知识点。单纯大模型回答缺少来源依据，传统关键词搜索又难以覆盖同义表达。因此项目将本地教材检索与多 Agent 问答结合，提升医学学习问答的可解释性和展示效果。

## 4. 目标用户

- 医学、生命科学和大健康方向学生
- 需要快速查阅本地教材的学习者
- 黑客松评委和现场演示用户

## 5. 核心功能

- Vue 产品化聊天界面
- FastAPI 后端 API
- PDF 教材读取和索引构建
- Embedding + TF-IDF hybrid 检索
- Agent 路由信息展示
- 教材片段引用展示
- ECharts 检索分数和来源分布可视化
- PDF 上传保存接口

## 6. 系统架构

- 前端：Vue 3、Vite、TypeScript、Ant Design Vue、Ant Design X 风格交互、ECharts。
- 后端：FastAPI、Uvicorn、Pydantic。
- 模型：魔搭 ModelScope API-Inference，按 OpenAI-compatible API 调用。
- RAG：本地 PDF 解析、chunk 切分、TF-IDF 索引、Embedding 索引和缓存。

## 7. 多 Agent 流程

1. Router / Query Planner Agent 判断用户意图。
2. 问候类问题直接回复，不检索 PDF。
3. 医学学习问题生成关键词和 expanded query。
4. 症状问题生成检索任务，并要求回答时安抚用户、避免诊断。
5. PDF Search Agent 检索教材片段。
6. Answer Agent 结合检索结果输出结构化回答和安全提示。

## 8. Hybrid RAG 检索

系统支持 Embedding 语义检索和 TF-IDF 关键词检索。Hybrid 模式会对原始问题、扩展问题和关键词分别检索，再按 `source_file + page + chunk_id` 合并去重，并保留命中方式。Embedding 失败时自动 fallback 到 TF-IDF。

## 9. 前端交互设计

前端包含 Conversations 会话列表、Chat Bubble、Sender 输入框、Agent 路由信息面板、教材片段引用面板和 ECharts 可视化。ECharts 包括检索片段相似度柱状图和来源教材分布饼图。

## 10. 部署与访问方式

当前优先支持同一局域网展示：后端监听 `0.0.0.0:8000`，前端监听 `0.0.0.0:5173`，浏览器访问电脑局域网 IP。后续可扩展为前端构建后由 Nginx 或 FastAPI 托管，也可部署到云服务器或 ModelScope 创空间。

## 11. 医学安全边界

系统仅用于学习与信息辅助理解，不能替代医生诊断和治疗建议。症状类问题不输出确定性诊断，不给出替代临床决策的治疗方案，并提示必要时就医。

## 12. 当前不足

- Ant Design X Vue 原生组件后续仍可进一步替换，目前使用 Ant Design Vue 模拟 X 风格交互。
- 扫描版 PDF 如果没有 OCR 文本，解析效果有限。
- Embedding 依赖远程 API，速度和稳定性受网络和模型服务影响。
- 暂未实现生产级用户鉴权、任务队列和日志审计。

## 13. 后续优化方向

- 接入异步索引构建任务和进度条。
- 用 Ant Design X Vue 原生 Bubble、Sender、Conversations 组件替换自定义实现。
- 增加 OCR、章节识别和页码跳转。
- 增加检索重排序和引用一致性校验。
- 支持前端构建产物由 FastAPI 或 Nginx 托管。

## 14. GitHub 链接占位

GitHub：待填写

## 15. 部署链接占位

在线演示：待填写
