# HealthPDF Agent Agent 架构说明

## 1. Router Agent

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

职责：识别意图、提取主题和关键词，对普通问候不强制检索 PDF。

## 2. Parser Agent / Parser Service

输入：本地教材文件。当前优先支持 PDF。

输出：统一 chunk 结构，包括 `chunk_id`、`book`、`source_file`、`chapter`、`page`、`text`、`char_count`。

职责：解析教材、保留页码和来源。章节识别不稳定时使用“章节待识别”，不阻塞索引构建。

## 3. Retrieval Agent

输入：query、topic、node_name、graph_context。

输出：统一 evidence：

```json
{
  "evidence_id": "ev_001",
  "book": "病理生理学",
  "source_file": "07_病理生理学.pdf",
  "chapter": "章节待识别",
  "page": 123,
  "quote": "原文短摘录",
  "score": 0.82,
  "match_type": "tfidf"
}
```

职责：统一服务知识小回答、图谱构建、节点详情和报告生成。`RETRIEVAL_BACKEND=tfidf` 可稳定兜底。

## 4. Graph Agent

输入：`topic`、`evidence_list`、可选 `current_graph_state` 和 `user_followup`。

输出：GraphJSON 或 graph patch。节点和边都带 `evidence_ids`。

职责：基于证据生成可视化知识图谱，支持增量新增节点和边。

## 5. Integration Agent

输入：node、evidence_list、graph_state、feedback_action。

输出：重复分析、互补分析、压缩比、反馈后的 graph。

职责：识别跨教材重复、互补和缺失，处理教师反馈动作。

## 6. Answer & Report Agent

输入：question/topic/node/graph/evidence。

输出：知识小回答、知识闪卡、节点详情、Markdown 报告。

职责：所有生成内容都基于 evidence，不编造教材来源、页码或章节。

## 数据流

```text
用户输入
→ Router Agent 判断意图
→ Retrieval Agent 从统一索引检索 evidence
→ Ask: Answer Agent 生成回答 + 引用 + 闪卡
→ Graph: Graph Agent 生成 GraphJSON
→ Node: Answer Agent 生成节点详情
→ Feedback: Integration Agent 修改 graph 并记录反馈
→ Report: Answer & Report Agent 导出 Markdown
```
