# HealthPDF Agent 技术报告

## 1. 项目名称

HealthPDF Agent：面向医学教材的学科知识整合智能体

## 2. 项目摘要

HealthPDF Agent 围绕 7 本医学教材构建统一 RAG 证据层，提供知识小回答和知识图谱工作台。系统可检索教材原文证据，生成带引用的简洁回答、知识闪卡、跨教材知识图谱、节点详情、教师反馈记录和 Markdown 整合报告。

## 3. 问题背景

医学教材内容庞大且跨学科关联密集。教师和学生不仅需要问答，还需要看到知识点在多本教材中的重复、互补和缺失关系。普通 PDF 问答难以支撑知识整合、图谱可视化和反馈式修订。

## 4. 目标用户

- 医学课程教师
- 医学生和生命科学方向学生
- 黑客松评审与现场演示用户

## 5. 核心功能

- 知识小回答：问题 → RAG 证据 → 简洁回答 + 引用 + 闪卡。
- 知识图谱工作台：主题 → 跨教材 evidence → GraphJSON → ECharts graph。
- 节点详情：定义、解释、重复/互补分析、教材来源。
- 教师反馈：保留、删除、拆分、合并、修改说明。
- 报告导出：Markdown 跨教材整合报告。

## 6. 系统架构

- 前端：Vue 3 + Vite + Ant Design Vue + ECharts graph。
- 后端：FastAPI + Pydantic。
- 模型：ModelScope OpenAI-compatible API。
- RAG：本地 PDF 解析、chunk、TF-IDF / hybrid 检索、统一 evidence schema。

## 7. 多 Agent 流程

Router Agent 识别意图；Parser Agent 解析教材；Retrieval Agent 提供统一证据；Graph Agent 生成图谱；Integration Agent 做跨教材分析和反馈处理；Answer & Report Agent 生成回答、节点详情和报告。

## 8. RAG 证据层

RAG 不只服务问答，也服务图谱构建、节点详情、跨教材整合和报告导出。所有引用都来自 evidence，包含教材名、页码、章节占位和原文摘录。

## 9. 跨教材整合

系统按 evidence 的教材来源聚合节点证据，识别多书共同出现的重复知识点，以及不同教材在定义、机制、诊断、治疗等维度的互补信息。证据不足的部分会明确标注。

## 10. 教师反馈

教师可对节点执行保留、删除、拆分、合并、修改说明。后端记录 feedback_record，并把状态写回 graph，用于报告导出。

## 11. 报告导出

报告包含主题概述、图谱摘要、主要节点、重复/互补/缺失分析、教师反馈、压缩比说明和教材引用来源。引用不编造，全部来自 GraphJSON 的 evidence。

## 12. 当前不足

- 多格式解析目前 PDF 优先，docx/txt/md 仅保留扩展方向。
- 章节识别仍是轻量启发式，不保证完全准确。
- 图谱生成是证据驱动的规则化 Demo，后续可接入更强 LLM JSON 生成与校验。
- 前端会话尚未持久化。

## 13. 后续优化方向

- OCR 和章节目录识别。
- 更严格的 GraphJSON 校验和图谱 patch 动画。
- 教师多轮反馈历史持久化。
- 检索重排序和跨教材缺失检测增强。
- 前端构建产物托管和公网部署。

## 14. GitHub 链接占位

GitHub：待填写

## 15. 部署链接占位

在线演示：待填写
