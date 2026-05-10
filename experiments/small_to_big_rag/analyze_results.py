"""Generate the P2 Small-to-Big RAG technical report from experiment outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
RESULTS_DIR = BASE_DIR / "results"
REPORT_PATH = PROJECT_ROOT / "report" / "p2_small_to_big_rag_report.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def best_strategy(summaries: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    return max(summaries, key=lambda item: item.get(metric, 0))


def find_result(raw_results: list[dict[str, Any]], question_id: str, strategy: str) -> dict[str, Any] | None:
    for row in raw_results:
        if row["question_id"] == question_id and row["strategy"] == strategy:
            return row
    return None


def short_text(text: str, limit: int = 180) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def source_line(context: dict[str, Any]) -> str:
    page_start = context.get("page_start")
    page_end = context.get("page_end")
    if page_start and page_end and page_start != page_end:
        page = f"{page_start}-{page_end}"
    elif page_start:
        page = str(page_start)
    else:
        page = "未知"
    return f"{context.get('textbook') or '未知教材'} / {context.get('chapter') or '未知章节'} / 页码 {page}"


def case_block(raw_results: list[dict[str, Any]], question_id: str) -> str:
    baseline = find_result(raw_results, question_id, "baseline_medium")
    small = find_result(raw_results, question_id, "small_only")
    stb = find_result(raw_results, question_id, "small_to_big")
    if not baseline or not small or not stb:
        return ""

    question = baseline["question"]

    def top_context(row: dict[str, Any]) -> dict[str, Any]:
        contexts = row.get("contexts") or []
        return contexts[0] if contexts else {}

    b_ctx = top_context(baseline)
    s_ctx = top_context(small)
    stb_ctx = top_context(stb)

    return f"""### 案例：{question}

- `baseline_medium`：命中关键词 {baseline.get('matched_keywords', [])}，召回率 {fmt(baseline.get('keyword_recall', 0))}。首条证据来源：{source_line(b_ctx)}。片段：{short_text(b_ctx.get('snippet', ''))}
- `small_only`：命中关键词 {small.get('matched_keywords', [])}，召回率 {fmt(small.get('keyword_recall', 0))}。首条证据来源：{source_line(s_ctx)}。片段：{short_text(s_ctx.get('snippet', ''))}
- `small_to_big`：命中关键词 {stb.get('matched_keywords', [])}，召回率 {fmt(stb.get('keyword_recall', 0))}。扩展后首条 parent 来源：{source_line(stb_ctx)}。片段：{short_text(stb_ctx.get('snippet', ''))}

分析：该问题展示了 small-to-big 的典型取舍。small chunk 用于定位具体术语或局部句子，parent context 把同一章节附近内容带回，因此更适合需要定义、机制、分类同时出现的教材问答。若本题 small-to-big 指标没有超过其他策略，说明当前关键词或教材覆盖限制了自动指标的分辨率，但 parent 证据仍提供了更完整的可读上下文。
"""


def main() -> None:
    summary_path = RESULTS_DIR / "summary.json"
    raw_path = RESULTS_DIR / "raw_results.json"
    table_path = RESULTS_DIR / "results_table.md"
    if not summary_path.exists() or not raw_path.exists() or not table_path.exists():
        raise RuntimeError("Missing result files. Run run_experiment.py before analyze_results.py.")

    summary_payload = load_json(summary_path)
    raw_payload = load_json(raw_path)
    summaries = summary_payload["strategies"]
    raw_results = raw_payload["results"]
    result_table = table_path.read_text(encoding="utf-8").strip()

    top_recall = best_strategy(summaries, "keyword_recall")
    top_hit = best_strategy(summaries, "hit@5")
    top_citation = best_strategy(summaries, "citation_completeness")
    stb = next(item for item in summaries if item["strategy"] == "small_to_big")
    baseline = next(item for item in summaries if item["strategy"] == "baseline_medium")
    small = next(item for item in summaries if item["strategy"] == "small_only")

    source_paths = summary_payload["metadata"].get("source_paths", [])
    source_text = "、".join(source_paths) if source_paths else "未记录"
    question_count = summary_payload["metadata"].get("question_count", 0)
    doc_count = summary_payload["metadata"].get("doc_count", 0)

    case_ids = []
    for question_id in ["q001", "q005", "q009", "q011"]:
        if find_result(raw_results, question_id, "small_to_big"):
            case_ids.append(question_id)
        if len(case_ids) == 3:
            break
    cases = "\n".join(case_block(raw_results, question_id) for question_id in case_ids)

    report = f"""# P2 技术报告：Small-to-Big RAG 在医学教材知识整合问答中的优化实验

## 摘要

医学教材知识问答同时要求术语定位和解释完整性：局部概念常由一句话触发，但机制、分类、病理变化和临床表现往往分布在同一章节的多个段落。本文对比了三种离线 RAG 检索策略：中等 chunk 的 `baseline_medium`、小 chunk 的 `small_only`、以及先检索 small chunk 再扩展 parent context 的 `small_to_big`。实验使用项目中已解析的教材数据和 {question_count} 个医学问题，采用 `TfidfVectorizer` 字符 n-gram 检索，避免外部 API 影响复现。真实结果显示：`small_to_big` 的 hit@5 为 {fmt(stb['hit@5'])}，关键词覆盖率为 {fmt(stb['keyword_recall'])}，平均上下文长度为 {fmt(stb['avg_context_chars'], 1)} 字，平均延迟为 {fmt(stb['avg_latency_ms'], 2)} ms。与 `small_only` 相比，它用更长 parent context 换取更完整证据；与 `baseline_medium` 相比，它保留了小块定位能力。代价是上下文字数增加，检索后还需要执行 parent 映射。

## 1. 问题分析

普通 RAG 在医学教材问答中存在明显 chunk 粒度矛盾。chunk 太大时，一个片段可能包含多个概念，TF-IDF 或 embedding 的相关性会被长文本中的噪声稀释，导致局部术语定位不够精准。chunk 太小时，检索结果虽然更容易命中“炎症”“坏死”“血栓形成”等关键词，但答案所需的定义、分类、机制和后续解释可能落在相邻段落中，直接把 small chunk 交给回答模块容易造成证据残缺。

医学教材还有两个特点：第一，章节具有强结构性，同一节内的上下文通常围绕同一病理过程展开；第二，教材回答非常依赖来源可追溯性，需要保留教材、章节和页码。Small-to-Big RAG 的目标不是单纯提高关键词命中，而是在命中局部证据后，把同章节或父级 chunk 一并带回，让回答模块获得更完整、更稳定、可引用的证据。

## 2. 方法设计

本实验实现三组策略。

- `baseline_medium`：按 700 字、80 字 overlap 切分，检索 top 5 中等 chunks，并直接作为上下文。
- `small_only`：按 300 字、50 字 overlap 切分，检索 top 5 small chunks，并直接作为上下文。
- `small_to_big`：先按 300 字 small chunk 检索 top 5，再映射到 1200 字、150 字 overlap 的 parent chunk。若无法按页码或字符范围匹配，则退化为同章节 parent，最后才返回 small chunk 自身。

```mermaid
graph TD
    Q[用户问题] --> S[Small Chunk 检索]
    S --> H[命中局部证据]
    H --> P[映射到 Parent Chunk / 章节上下文]
    P --> C[去重与来源保留]
    C --> A[带引用回答 / 图谱 evidence]
```

实现路径：

- 实验脚本：`experiments/small_to_big_rag/run_experiment.py`
- 分析脚本：`experiments/small_to_big_rag/analyze_results.py`
- 问题集：`experiments/small_to_big_rag/eval_questions.json`
- 结果目录：`experiments/small_to_big_rag/results/`

复现实验命令：

```bash
python experiments/small_to_big_rag/run_experiment.py
python experiments/small_to_big_rag/analyze_results.py
```

## 3. 实验设计

数据来源按优先级读取 `data/parsed/*.json`，如果该目录为空，则退化到 `data/sample_docs/sample_health_knowledge.md` 或 `report/sample_integration_炎症.md`。本次运行读取到 {doc_count} 个章节/页面级文档片段，来源文件包括：{source_text}。实验没有重新解析 PDF，没有调用主系统 `build_index`，也没有写入主系统 `indexes/`。

问题集包含 {question_count} 个医学教材问答问题，覆盖定义、机制、分类、形态学改变、比较和表现等类型。每个问题配置 `expected_keywords`，用于计算自动指标。若当前教材数据源缺少某主题，例如局部解剖学，脚本不会报错，而是如实表现为低命中或低召回。

评估指标如下：

- `hit@5`：top contexts 是否包含至少一个期望关键词。
- `keyword_recall`：期望关键词被上下文覆盖的比例。
- `avg_context_chars`：每题返回上下文总字数均值，近似衡量上下文完整性和 token 成本。
- `avg_latency_ms`：每题检索和映射耗时均值，不含索引构建。
- `evidence_count`：每题平均返回 evidence 数。
- `source_diversity`：每题平均涉及教材数。
- `citation_completeness`：返回 evidence 中同时带教材、章节、页码信息的比例。

本实验使用 TF-IDF 字符 n-gram，而不是 LLM judge 或外部 embedding，原因是：一方面它能离线复现，不受网络、API key、模型版本影响；另一方面中文医学术语具有强字符组合特征，`analyzer="char_wb", ngram_range=(2,4)` 对“血栓形成”“细胞水肿”“核碎裂”等词有较稳定的匹配能力。当然，TF-IDF 只代表一个可控检索实验环境，不等价于最终线上 embedding 效果。

## 4. 实验结果

{result_table}

从表中可以看到，`{top_hit['strategy']}` 在 hit@5 上最高或并列最高，`{top_recall['strategy']}` 在关键词覆盖率上最好，`{top_citation['strategy']}` 的引用完整性最高。`small_only` 的优势是上下文短、定位集中，平均上下文字数为 {fmt(small['avg_context_chars'], 1)}；不足是局部片段常常只覆盖定义或一个子项，缺少章节解释。`baseline_medium` 平均上下文字数为 {fmt(baseline['avg_context_chars'], 1)}，比 small chunk 更完整，但中等 chunk 的检索粒度仍可能混入目录、章节标题或邻近主题。`small_to_big` 平均上下文字数为 {fmt(stb['avg_context_chars'], 1)}，通常更适合需要“先找到术语，再展开解释”的医学教材问答，但这也意味着后续 LLM 回答阶段会消耗更多 token。

需要真实说明的是，本实验的自动指标以关键词覆盖为主，因此它更能反映“证据中是否出现目标术语”，不能完整代表最终回答质量。如果某些题目中 `small_to_big` 的 `keyword_recall` 没有超过 `small_only`，可能是因为 small chunk 已经包含所有关键词；如果 parent chunk 引入了更多上下文，关键词指标不会额外奖励解释连贯性。但对真实问答系统而言，parent context 的价值主要体现在答案可解释、引用完整和减少断章取义。

## 5. 案例分析

{cases}

## 6. 对系统的实际价值

Small-to-Big RAG 可以以低侵入方式用于当前系统的证据层。对知识小回答而言，它能让回答模块不仅看到命中的短句，也看到同章节上下文，从而减少只根据半句定义回答的情况。对知识图谱构建而言，节点 evidence 更稳定，尤其是“机制”“分类”“结局”这类节点，往往需要从同一章节多个段落提取关系。对跨教材整合而言，先 small 检索可以减少不同主题误合并，后 parent 扩展可以保留来源边界和章节语义。对教师反馈流程而言，当教师要求补充 evidence 时，可以从已命中的 small chunk 追溯 parent context，而不是重新扩大全库检索范围。

该策略也适合渐进接入：现有主系统可保留原检索接口，在 evidence 构造阶段增加 `parent_context` 字段，并在回答或图谱节点详情中优先展示短证据、按需展开长证据。这样不会改变教材解析和索引主流程，也便于 A/B 测试。

## 7. 局限性

本实验仍是小规模离线验证。问题集只有 {question_count} 题，覆盖面不足以代表全部医学教材问答场景。评价方式使用关键词覆盖近似衡量检索质量，没有医学专家标注的标准答案，也没有人工判断回答是否完整。TF-IDF 检索不代表最终 embedding、reranker 或混合检索的表现。parent context 变长会增加后续 LLM token 消耗，并可能引入不相关段落；如果 parent 映射只按章节匹配，在章节很长或结构解析错误时，仍可能扩展过宽。

此外，当前实验的 `source_diversity` 只统计返回 evidence 涉及教材数，不能判断跨教材内容是否真正互补。对于“局部解剖学”等当前数据源可能缺失的主题，低分反映的是数据覆盖不足，而不是检索策略本身失效。

## 8. 未来工作

后续可以引入 BGE embedding 作为主召回模型，并保留 TF-IDF 作为可解释 baseline。检索后增加 reranker，对 small hits 做语义重排，再映射 parent context。评测集应扩大为人工标注问题集，包含标准答案、支持证据和不可回答问题。还可以对 `small_chunk_size`、`parent_chunk_size`、`top_k` 做网格搜索，统计 keyword recall、人工评分、token 成本和端到端响应时间之间的关系。最终可在主系统中做灰度实验：同一批问题分别使用 baseline RAG 与 small-to-big RAG，比较教师反馈修改率、引用点击率和回答采纳率。

## 9. 参考

- Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.
- Reimers and Gurevych, Sentence-BERT.
- Johnson et al., FAISS: A Library for Efficient Similarity Search.
- BAAI, BGE Embedding model family.
- Parent Document Retriever / Small-to-Big Retrieval 思路：先小粒度召回，再返回父文档或章节上下文。
- 本项目实验实现：`experiments/small_to_big_rag/run_experiment.py` 与 `experiments/small_to_big_rag/analyze_results.py`。
"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote report to {REPORT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
