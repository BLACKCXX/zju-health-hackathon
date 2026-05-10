# HealthPDF Agent：学科知识整合智能体

## 一键部署

```bash
docker compose up -d --build
```

访问前端：

```text
http://localhost:15173
```

后端健康检查：

```text
http://localhost:18000/api/health
```

运行测试：

```bash
pytest tests/
```

样例整合报告：[report/sample_integration_炎症.md](report/sample_integration_炎症.md)


HealthPDF Agent 是面向 7 本医学教材的"学科知识整合智能体"Demo。系统以 RAG 作为统一证据层，支持教材管理、标准 RAG Pipeline、知识小回答、跨教材知识图谱工作台、节点详情、教师反馈和 Markdown 整合报告导出。

## 三大核心模式

### 1. 教材管理 Textbook Manager

上传 PDF / Markdown / TXT 格式教材，支持：
- 拖拽上传和点击选择
- 自动解析提取章节结构
- 显示解析状态（等待/解析中/完成/失败）
- 查看章节结构和正文预览
- 建立 RAG 索引（chunk → embedding → 向量检索）

### 2. 知识小回答 Ask Mode

用户输入医学教材相关问题后，系统会：

- 识别核心关键词和知识点；
- 从本地教材 RAG 索引检索 top-5 相关 chunk；
- 生成简洁回答；
- 展示教材名、章节、页码、相关度和原文短摘录；
- 生成知识闪卡；
- 点击闪卡可进入知识图谱工作台。

### 3. 知识图谱工作台 Graph Workspace

用户输入主题，例如"高血压"，系统会：

- 基于统一 RAG 证据层检索多本教材（每本 top-k，全球 top-k）；
- 生成带 evidence_ids 的 GraphJSON；
- 用 ECharts graph 展示可拖拽、可缩放、可点击图谱；
- 点击节点显示定义、解释、跨教材重复/互补分析和来源；
- 支持教师反馈：保留、删除、拆分、合并、修改说明；
- 支持导出 Markdown 跨教材整合报告。

## Agent 架构

### 数据流

```text
用户输入 → Router Agent 判断意图
         → Retrieval Agent 从统一索引检索 evidence
         → Ask: Answer Agent 生成回答 + 引用 + 闪卡
         → Graph: Graph Agent 生成 GraphJSON
         → Node: Answer Agent 生成节点详情
         → Feedback: Integration Agent 修改 graph 并记录反馈
         → Report: Answer & Report Agent 导出 Markdown
```

### Router Agent

输入：`user_query`、`current_mode`、可选 `current_graph_state`。

输出：
```json
{
  "intent": "ask | graph_build | graph_update | node_detail | feedback | report | greeting | unknown",
  "topic": "...",
  "keywords": ["..."],
  "need_retrieval": true,
  "reason": "..."
}
```

### Parser Agent / Document Parser

输入：本地教材文件（PDF / Markdown / TXT）。

输出：统一 textbook 结构，包括 `textbook_id`、`filename`、`title`、`chapters[chapter_id/title/page_start/page_end/content]`。

职责：解析教材、保留页码和来源，章节识别基于正则（第X章、Chapter X）。

### Textbook Store

持久化解析后的教材 JSON 到 `data/parsed/{textbook_id}.json`。

### Retrieval Agent

输入：query、topic、node_name、graph_context。

输出：统一 evidence：
```json
{
  "evidence_id": "ev_001",
  "book": "病理生理学",
  "source_file": "07_病理生理学.pdf",
  "chapter": "第四章 炎症",
  "page": 78,
  "quote": "原文短摘录",
  "score": 0.82,
  "match_type": "embedding"
}
```

职责：统一服务知识小回答、图谱构建、节点详情和报告。检索后端支持 faiss / tfidf / hybrid。

### Graph Agent

输入：`topic`、`evidence_list`、可选 `current_graph_state` 和 `user_followup`。

输出：GraphJSON 或 graph patch。节点和边都带 `evidence_ids`。

### Integration Agent

输入：node、evidence_list、graph_state、feedback_action。

输出：重复分析、互补分析、压缩比、反馈后的 graph。

### Answer & Report Agent

输入：question/topic/node/graph/evidence。

输出：知识小回答、知识闪卡、节点详情、Markdown 报告。

职责：所有生成内容都基于 evidence，不编造教材来源、页码或章节。

## 标准 RAG Pipeline

### Step 1: Chunking

- 从 parsed textbook JSON 读取 chapters/pages
- 按 700 字切 chunk（可配置 CHUNK_SIZE=700）
- overlap 80 字（可配置 CHUNK_OVERLAP=80）
- 每个 chunk 保留 metadata：textbook_id、book、source_file、chapter、page_start、page_end、chunk_id

### Step 2: Embedding

- 优先使用本地 sentence-transformers 模型
- 默认：`BAAI/bge-small-zh-v1.5`
- fallback：`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- 再 fallback 到 API embedding
- 最终 fallback 到 TF-IDF（前端标注 fallback 模式）

### Step 3: Vector Store

- 优先 FAISS
- fallback 到 numpy cosine similarity
- 最终 fallback 到 TF-IDF
- 保存到 `indexes/healthpdf_index.pkl`

### Step 4: Query

- 用户问题 → embedding → top-5 检索
- 返回 answer + citations + source_chunks

### Step 5: Answer

- LLM prompt 必须包含：
  - 只能基于提供的上下文回答
  - 不得使用模型自身知识补充
  - 每个回答附带来源引用，格式为 [教材名称, 章节, 第 X 页]
  - 如果上下文中找不到答案，回答"当前知识库中未找到相关信息"

## 环境变量

不要覆盖已有 `.env`。真实 API key 只放在项目根目录 `.env`，不提交 Git。

`.env.example` 只保留模板：

```env
DEFAULT_API_KEY=your_modelscope_sdk_token_here
DEFAULT_BASE_URL=https://api-inference.modelscope.cn/v1/
DEFAULT_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
ROUTER_MODEL=Qwen/Qwen3-14B
SUMMARY_MODEL=Qwen/Qwen3-14B
GRAPH_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507

RETRIEVAL_BACKEND=faiss
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

CHUNK_SIZE=700
CHUNK_OVERLAP=80
RAG_TOP_K=5
GRAPH_TOP_K_PER_BOOK=5
GRAPH_GLOBAL_TOP_K=30

TEXTBOOK_DIR=textbooks
UPLOAD_DIR=uploads
INDEX_DIR=indexes
OUTPUT_DIR=outputs
```

关键说明：
- `RETRIEVAL_BACKEND=faiss`：优先向量检索
- `EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5`：本地中文 embedding 模型
- `CHUNK_SIZE=700`、`CHUNK_OVERLAP=80`：符合赛题要求的分块策略
- `RAG_TOP_K=5`：检索 top-5 相关 chunk
- `GRAPH_TOP_K_PER_BOOK=5`、`GRAPH_GLOBAL_TOP_K=30`：图谱每本取 5，全球取 30

## 本地教材

将赛方 7 本教材 PDF 放在：

```text
textbooks/
```

`textbooks/`、PDF、`.env`、`indexes/*.pkl`、`outputs/` 都不会上传 GitHub。

## 后端运行

```bash
cd /mnt/e/Hackthon
conda activate zju_hackathon
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 18000 --reload
```

测试：

```bash
curl http://127.0.0.1:18000/api/health
curl http://127.0.0.1:18000/api/status
curl http://127.0.0.1:18000/api/rag/status
```

RAG 索引构建：

```bash
# 自动从 textbooks/ 建立索引
curl -X POST http://127.0.0.1:18000/api/rag/index \
  -H "Content-Type: application/json" \
  -d '{"source": "textbooks", "force": true, "chunk_size": 700, "chunk_overlap": 80}'

# RAG 问答测试
curl -X POST http://127.0.0.1:18000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "炎症是什么？", "top_k": 5}'
```

## 前端运行

```bash
cd /mnt/e/Hackthon/frontend
npm install --registry=https://registry.npmmirror.com
npm run dev -- --host 0.0.0.0 --port 15173
```

本机访问：

```text
http://127.0.0.1:15173
```

如需手机访问同一 Wi-Fi 下电脑服务，设置 `frontend/.env`：

```env
VITE_API_BASE_URL=http://电脑局域网IP:18000
```

手机浏览器打开：

```text
http://电脑局域网IP:15173
```

注意：`0.0.0.0` 只是监听地址，不是浏览器访问地址。

## 评审演示路径

### 教材管理演示

1. 打开前端首页，选择"教材管理"Tab
2. 拖拽上传 PDF / MD / TXT 文件
3. 查看文件列表（文件名、格式、状态）
4. 点击"批量解析"，观察章节结构生成
5. 点击"建立索引"，观察 RAG 索引构建过程
6. 查看索引状态（chunk 数、embedding 模型、检索后端）

### 知识小回答演示

1. 进入"知识小回答"模式
2. 输入"什么是炎症？"
3. 观察回答、引用来源（教材名、章节、页码、相关度）
4. 查看右侧知识闪卡
5. 点击闪卡"生成图谱"进入图谱工作台

### 知识图谱工作台演示

1. 输入主题"高血压"
2. 生成图谱，拖拽/缩放并点击节点
3. 右侧展示节点详情、跨教材重复/互补分析、来源证据
4. 使用教师反馈按钮记录"保留/删除/修改说明"
5. 点击"导出 Markdown 报告"下载整合报告

## Git 安全

```bash
git status --ignored
git check-ignore -v .env
git check-ignore -v textbooks/example.pdf
git check-ignore -v indexes/healthpdf_index.pkl
```

提交命令：

```bash
git add backend frontend src docs README.md .env.example .gitignore requirements.txt indexes/.gitkeep outputs/.gitkeep uploads/.gitkeep
git commit -m "Build discipline knowledge integration agent"
git push
```

## 医学安全边界

本系统仅用于学习与信息辅助理解，不能替代医生诊断和治疗建议。涉及症状、用药、治疗或紧急健康问题，应咨询专业医生或及时就医。
