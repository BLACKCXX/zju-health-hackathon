# HealthPDF Agent

HealthPDF Agent 是一个面向 AI×大健康场景的多 Agent PDF-RAG 问答网站。系统使用 Python + Gradio 构建，支持读取本地医学教材 PDF，构建本地检索索引，并通过魔搭 ModelScope API-Inference 的 OpenAI-compatible 接口生成带引用的结构化回答。

项目目标是黑客松可展示、可提前部署的最小闭环：网页能打开、能识别问题意图、能检索教材、能展示检索片段、能调用模型生成回答，并保留医学安全边界。

## 三 Agent 架构

- Router / Query Planner Agent：判断用户意图，区分问候、医学学习问题、症状问题和非医学问题；为需要检索的问题生成 `expanded_query`、`search_keywords` 和回答重点。
- PDF Search Agent：基于 Query Planner 的检索任务执行 hybrid retrieval，返回文件名、页码、chunk、相似度和命中方式。
- Answer Agent：根据用户问题、Query Plan 和教材片段生成回答。症状类问题会先安抚用户，并明确不做确定性诊断。

## Hybrid 检索

当前支持三种检索后端：

- `hybrid`：Embedding 语义检索 + TF-IDF 关键词检索，默认推荐。
- `embedding`：优先语义检索，失败时自动 fallback 到 TF-IDF。
- `tfidf`：仅使用本地 TF-IDF，不需要 embedding API。

Hybrid 流程：

```text
用户问题
→ Router / Query Planner 生成 expanded_query 和 keywords
→ original_query embedding 检索
→ expanded_query embedding 检索
→ original / expanded / keywords 的 TF-IDF 检索
→ 合并去重
→ Answer Agent 生成带引用回答
```

如果 embedding 调用失败，系统会保留并使用 TF-IDF 索引，不会让整个应用崩溃。

## 魔搭 API 配置

复制模板：

```bash
cp .env.example .env
```

在项目根目录 `.env` 中填写真实配置：

```env
DEFAULT_API_KEY=your_modelscope_sdk_token_here
DEFAULT_BASE_URL=https://api-inference.modelscope.cn/v1/
DEFAULT_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507

ROUTER_API_KEY=
ROUTER_BASE_URL=
ROUTER_MODEL=Qwen/Qwen3-14B

ANSWER_API_KEY=
ANSWER_BASE_URL=
ANSWER_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507

SUMMARY_API_KEY=
SUMMARY_BASE_URL=
SUMMARY_MODEL=Qwen/Qwen3-14B

RETRIEVAL_BACKEND=hybrid

EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
```

说明：

- `DEFAULT_API_KEY` 使用魔搭 SDK Token。
- `DEFAULT_BASE_URL=https://api-inference.modelscope.cn/v1/`。
- `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL` 为空时回退到默认配置。
- `EMBEDDING_MODEL` 可改为 `Qwen/Qwen3-Embedding-8B`，以魔搭模型详情页 API 调用示例为准。
- 如果 235B 模型调用慢或失败，可以临时把 `ANSWER_MODEL` 改成更小模型。
- `.env.example` 只是模板，`.env` 不上传 GitHub。

项目兼容旧变量名：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MODEL_NAME`。如果新的 `DEFAULT_*` 未配置，会自动回退到旧变量名。

## 教材与索引

将赛方提供的 PDF 放在本地：

```text
textbooks/
```

PDF、上传文件、真实索引缓存不会上传 GitHub。

提前构建全量 hybrid 索引：

```bash
python scripts/build_index.py --force --backend hybrid
```

构建轻量 debug 索引：

```bash
python scripts/build_index.py --force --debug --max-pages-per-pdf 20 --backend tfidf
python scripts/build_index.py --force --debug --max-pages-per-pdf 20 --backend hybrid
```

检查索引：

```bash
python scripts/check_index.py
```

测试 API：

```bash
python scripts/test_api.py
```

## 本地运行

Windows PowerShell：

```powershell
cd E:\Hackthon
conda activate zju_hackathon
pip install -r requirements.txt
python app.py
```

WSL：

```bash
cd /mnt/e/Hackthon
conda activate zju_hackathon
pip install -r requirements.txt
python app.py
```

本地浏览器访问：

```text
http://127.0.0.1:7860
```

不要在浏览器里访问 `0.0.0.0`。

开启 Gradio share：

```bash
GRADIO_SHARE=1 python app.py
```

PowerShell：

```powershell
$env:GRADIO_SHARE="1"; python app.py
```

## ModelScope 创空间部署

1. 上传代码到 GitHub。
2. 创空间选择 Gradio 应用。
3. 入口文件使用 `app.py`。
4. 在平台环境变量中配置 `DEFAULT_API_KEY`、`DEFAULT_BASE_URL`、`DEFAULT_MODEL`，按需配置 `EMBEDDING_MODEL`。
5. 部署环境若没有教材 PDF，页面会提示可使用普通聊天或上传 PDF 后构建临时索引。
6. 不要把 `.env`、PDF、`indexes/*.pkl`、`uploads/` 内容上传到 GitHub。

## Git 提交命令

```bash
git status
git add app.py src scripts requirements.txt README.md docs data .env.example .gitignore indexes/.gitkeep outputs/.gitkeep uploads/.gitkeep
git commit -m "Upgrade HealthPDF Agent hybrid RAG"
git push
```

提交前检查忽略规则：

```bash
git status --ignored
git check-ignore -v .env
git check-ignore -v textbooks/example.pdf
git check-ignore -v indexes/healthpdf_index.pkl
```

## 医学安全边界

本系统仅用于学习与信息辅助理解，不能替代医生诊断和治疗建议。系统不会给出确定性诊断；涉及症状、用药、治疗或紧急健康问题时，应咨询专业医生或及时就医。

## 当前限制

- Embedding 依赖远程 API，失败时会 fallback 到 TF-IDF。
- 扫描版 PDF 如果没有 OCR 文本，解析效果有限。
- Query Planner 有规则兜底，但模型输出质量会影响检索计划。
- 本项目不是医疗器械或临床诊断系统，不应用于真实诊断决策。
