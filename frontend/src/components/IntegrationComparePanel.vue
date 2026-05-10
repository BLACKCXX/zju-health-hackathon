<template>
  <a-card class="soft-card integration-compare" :bordered="false">
    <template #title>整合前后对比</template>

    <div class="compare-grid">
      <section class="compare-column">
        <h3>整合前</h3>
        <div class="metric-row">
          <span>原始 evidence 数</span>
          <strong>{{ evidenceCount }}</strong>
        </div>
        <div class="metric-row">
          <span>原始证据总字数</span>
          <strong>{{ originalChars }}</strong>
        </div>
        <div class="metric-row">
          <span>涉及教材数</span>
          <strong>{{ textbookCount }}</strong>
        </div>
        <div class="metric-row">
          <span>涉及章节数</span>
          <strong>{{ chapterCount }}</strong>
        </div>
      </section>

      <section class="compare-column">
        <h3>整合后</h3>
        <div class="metric-row">
          <span>节点数</span>
          <strong>{{ nodeCount }}</strong>
        </div>
        <div class="metric-row">
          <span>边数</span>
          <strong>{{ edgeCount }}</strong>
        </div>
        <div class="metric-row">
          <span>整合后摘要字数</span>
          <strong>{{ integratedChars }}</strong>
        </div>
        <div class="metric-row">
          <span>整合决策数</span>
          <strong>{{ decisionCount }}</strong>
        </div>
      </section>
    </div>

    <div class="compression-block">
      <div class="compression-header">
        <span>压缩比</span>
        <a-tag :color="compressionRatio <= 0.3 ? 'green' : 'orange'">
          {{ compressionRatio <= 0.3 ? '压缩比达标 ✓' : '压缩比偏高，建议继续压缩' }}
        </a-tag>
      </div>
      <a-progress
        :percent="compressionPercent"
        :stroke-color="compressionRatio <= 0.3 ? '#16a34a' : '#d97706'"
        size="small"
      />
      <div class="compression-detail">
        {{ originalChars }} → {{ integratedChars }} 字，ratio={{ compressionRatio.toFixed(2) }}
      </div>
    </div>

    <div class="decision-summary">
      <span>merge：{{ decisionStats.merge }}</span>
      <span>keep：{{ decisionStats.keep }}</span>
      <span>remove：{{ decisionStats.remove }}</span>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { GraphJSON } from '../types/graph'

const props = defineProps<{
  graph: GraphJSON | null
}>()

const evidence = computed(() => props.graph?.evidence || [])
const nodes = computed(() => props.graph?.nodes || [])
const edges = computed(() => props.graph?.edges || [])
const decisions = computed(() => props.graph?.decisions || [])

const evidenceCount = computed(() => evidence.value.length)
const nodeCount = computed(() => nodes.value.length)
const edgeCount = computed(() => edges.value.length)
const decisionCount = computed(() => decisions.value.length)

const originalChars = computed(() => {
  const fromGraph = props.graph?.integration?.compression?.original_chars
  if (typeof fromGraph === 'number' && fromGraph > 0) return fromGraph
  return evidence.value.reduce((sum, item) => sum + (item.quote || '').length, 0)
})

const integratedChars = computed(() => {
  const fromGraph = props.graph?.integration?.compression?.integrated_chars
  if (typeof fromGraph === 'number' && fromGraph > 0) return fromGraph
  return nodes.value.reduce((sum, item) => sum + (item.summary || '').length, 0)
})

const compressionRatio = computed(() => {
  const fromGraph = props.graph?.integration?.compression?.compression_ratio
  if (typeof fromGraph === 'number' && fromGraph >= 0) return fromGraph
  return integratedChars.value / Math.max(originalChars.value, 1)
})

const compressionPercent = computed(() => Math.min(100, Math.round(compressionRatio.value * 100)))

const textbookCount = computed(() => {
  const values = evidence.value
    .map((item: any) => item.textbook || item.book || item.source_file || '')
    .filter(Boolean)
  return new Set(values).size
})

const chapterCount = computed(() => {
  const values = evidence.value.map(item => item.chapter || '').filter(Boolean)
  return new Set(values).size
})

const decisionStats = computed(() => {
  const stats = { merge: 0, keep: 0, remove: 0 }
  for (const decision of decisions.value) {
    if (decision.action in stats) {
      stats[decision.action as keyof typeof stats] += 1
    }
  }
  return stats
})
</script>

<style scoped>
.integration-compare {
  color: #111827;
}

.compare-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.compare-column {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.compare-column h3 {
  margin: 0 0 10px;
  font-size: 15px;
  color: #111827;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}

.metric-row strong {
  color: #111827;
  font-weight: 700;
}

.compression-block {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.compression-header,
.decision-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 14px;
  color: #111827;
}

.compression-detail {
  margin-top: 6px;
  font-size: 13px;
  color: #4b5563;
}

.decision-summary {
  justify-content: flex-start;
  margin: 12px 0 0;
  color: #374151;
}

@media (max-width: 900px) {
  .compare-grid {
    grid-template-columns: 1fr;
  }
}
</style>
