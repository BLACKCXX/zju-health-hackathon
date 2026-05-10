# Small-to-Big RAG 检索策略实验

本目录只用于 P2 挑战加分项实验，不调用主系统服务，不重建主系统 `indexes/`，不修改 `backend/`、`frontend/`、`src/` 的业务逻辑。

## 实验目标

对比三种医学教材问答检索策略：

- `baseline_medium`：中等 chunk 直接检索。
- `small_only`：小 chunk 直接检索，提高局部定位。
- `small_to_big`：先检索 small chunk，再映射到 parent chunk / 章节上下文。

默认使用 `sklearn TfidfVectorizer` 的中文字符 n-gram 检索，保证离线、可复现、无需外部 API。

## 数据来源

脚本按优先级读取：

1. `data/parsed/*.json`
2. `data/sample_docs/sample_health_knowledge.md`
3. `report/sample_integration_炎症.md`

实验缓存和临时索引仅允许写入 `experiments/small_to_big_rag/artifacts/`。当前脚本默认不落地索引缓存，只保存评测结果。

## 运行命令

运行实验：

```bash
python experiments/small_to_big_rag/run_experiment.py
```

生成报告：

```bash
python experiments/small_to_big_rag/analyze_results.py
```

一键运行：

```bash
python experiments/small_to_big_rag/run_experiment.py && python experiments/small_to_big_rag/analyze_results.py
```

## 输出文件

- `results/raw_results.json`：每个问题、每个策略的原始检索结果。
- `results/summary.json`：按策略汇总后的指标。
- `results/results.csv`：表格化实验结果。
- `results/results_table.md`：可直接放入报告的 Markdown 表格。
- `../../report/p2_small_to_big_rag_report.md`：中文技术报告。
