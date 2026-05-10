# HealthPDF Agent

HealthPDF Agent 是一个面向 AI×大健康教材问答的多 Agent PDF-RAG 网站。当前主展示架构已经切换为 Vue 3 + Ant Design Vue + ECharts 前端，以及 FastAPI 后端。后端复用 `src/` 下已有的 Router / Query Planner Agent、PDF Search Agent、Answer Agent、Hybrid 检索和 ModelScope API 调用逻辑。

## 架构

```text
用户浏览器
→ Vue 前端
→ FastAPI 后端 API
→ src/rag_pipeline.py
→ Router Agent / PDF Search Agent / Answer Agent
→ ModelScope API + 本地 PDF 索引
→ 返回 answer、route_info、retrieved_chunks
→ Vue 展示聊天、Agent 路由、教材引用、ECharts 图表
```

## 核心功能

- Router / Query Planner Agent：判断问候、医学学习问题、症状问题，并生成检索关键词和 expanded query。
- PDF Search Agent：执行 Embedding + TF-IDF hybrid 检索，返回来源文件、页码、相似度和命中方式。
- Answer Agent：生成结构化回答；症状类问题会先安抚用户，不做确定性诊断。
- Vue 前端：会话列表、Chat Bubble、Sender 输入框、Agent 路由信息、教材引用片段、ECharts 检索可视化。
- FastAPI 后端：提供 `/api/health`、`/api/status`、`/api/chat`、`/api/build-index`、`/api/index-status`、`/api/upload-pdf`。

## API 配置

复制模板：

```bash
cp .env.example .env
```

真实 API key 只放在项目根目录 `.env` 中，不上传 GitHub。

关键配置：

```env
DEFAULT_API_KEY=your_modelscope_sdk_token_here
DEFAULT_BASE_URL=https://api-inference.modelscope.cn/v1/
DEFAULT_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
RETRIEVAL_BACKEND=hybrid
```

模型 ID 以魔搭模型详情页 API 调用示例为准。如果大模型调用慢或失败，可以临时把 `ANSWER_MODEL` 改成更小模型。

## 后端启动

Windows PowerShell：

```powershell
cd E:\Hackthon
conda activate zju_hackathon
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

WSL：

```bash
cd /mnt/e/Hackthon
conda activate zju_hackathon
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

本机 API 测试：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/status
```

## 前端启动

```bash
cd /mnt/e/Hackthon/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

本地浏览器访问：

```text
http://127.0.0.1:5173
```

前端环境变量模板：

```bash
cp frontend/.env.example frontend/.env
```

默认：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 手机同 Wi-Fi 访问

1. 启动后端：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

2. 启动前端：

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

3. Windows PowerShell 查看电脑局域网 IP：

```powershell
ipconfig
```

4. 手机和电脑连接同一 Wi-Fi。

5. 设置 `frontend/.env`：

```env
VITE_API_BASE_URL=http://电脑局域网IP:8000
```

6. 手机浏览器打开：

```text
http://电脑局域网IP:5173
```

注意：`0.0.0.0` 只是监听地址，不是浏览器访问地址；`127.0.0.1` 只代表本机。

## 索引构建

提前构建 hybrid 索引：

```bash
python scripts/build_index.py --force --backend hybrid
```

轻量 debug 索引：

```bash
python scripts/build_index.py --force --debug --max-pages-per-pdf 20 --backend tfidf
python scripts/build_index.py --force --debug --max-pages-per-pdf 20 --backend hybrid
```

检查索引：

```bash
python scripts/check_index.py
```

也可以在 Vue 页面左侧控制面板中构建或检查索引。

## 部署方式

方式 A：同一局域网展示

- 后端监听 `0.0.0.0:8000`
- 前端监听 `0.0.0.0:5173`
- 评委手机或电脑访问 `http://电脑局域网IP:5173`

方式 B：前端构建 + 后端服务

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/`。后续可由 FastAPI 或 Nginx 托管，本次黑客松优先使用开发服务器展示。

方式 C：临时公网

后续可按需要接入内网穿透、云服务器或 ModelScope 创空间。当前优先目标是 Vue + FastAPI 在同一网络可访问。

## Git 提交

```bash
git status
git add backend frontend src scripts requirements.txt README.md docs .env.example .gitignore indexes/.gitkeep outputs/.gitkeep uploads/.gitkeep
git commit -m "Add Vue FastAPI product UI"
git push
```

提交前检查：

```bash
git status --ignored
git check-ignore -v .env
git check-ignore -v frontend/.env
git check-ignore -v textbooks/example.pdf
git check-ignore -v indexes/healthpdf_index.pkl
```

## 医学安全边界

本系统仅用于学习与信息辅助理解，不能替代医生诊断和治疗建议。系统不会给出确定性诊断；涉及症状、用药、治疗或紧急健康问题时，应咨询专业医生或及时就医。
