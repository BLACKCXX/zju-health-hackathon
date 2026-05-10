<template>
  <a-card class="soft-card detail-card" :bordered="false">
    <template #title>节点详情</template>
    <a-empty v-if="!node" description="点击图谱节点查看详情" />
    <div v-else>
      <h2>{{ node.name }}</h2>
      <a-space wrap style="margin-bottom: 12px">
        <a-tag color="blue">{{ node.type }}</a-tag>
        <a-tag color="green">置信度 {{ ((node.confidence || 0) * 100).toFixed(0) }}%</a-tag>
        <a-tag v-if="node.chapter" color="purple">{{ node.chapter }}</a-tag>
        <a-tag v-if="node.page">第 {{ node.page }} 页</a-tag>
      </a-space>
      <p v-if="node.summary" class="summary">{{ node.summary }}</p>
      <a-divider />
      <h4>详细解释</h4>
      <p class="detail-text">{{ detail?.detail || '点击节点后由后端基于证据生成详细解释。' }}</p>
      <template v-if="node.book_sources?.length">
        <h4>来源教材</h4>
        <a-space wrap style="margin-bottom: 8px">
          <a-tag v-for="book in node.book_sources" :key="book" color="cyan">{{ book }}</a-tag>
        </a-space>
      </template>
      <template v-if="detail?.overlap_analysis">
        <h4>跨教材重复分析</h4>
        <p class="detail-text">{{ detail.overlap_analysis }}</p>
      </template>
      <template v-if="detail?.complement_analysis">
        <h4>跨教材互补分析</h4>
        <p class="detail-text">{{ detail.complement_analysis }}</p>
      </template>
      <template v-if="detail?.sources?.length">
        <h4>证据引用</h4>
        <div
          v-for="(item, idx) in (detail?.sources || [])"
          :key="idx"
          class="quote-card"
        >
          <div class="quote-book">{{ item.book }} · {{ item.chapter }} · 第 {{ item.page }} 页</div>
          <div class="quote-text">{{ item.quote }}</div>
        </div>
      </template>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { NodeDetailResponse } from '../types/api'
import type { GraphNode } from '../types/graph'

defineProps<{
  node: GraphNode | null
  detail: NodeDetailResponse | null
}>()
</script>

<style scoped>
.detail-card {
  max-height: 560px;
  overflow: auto;
}
.detail-card :deep(.ant-card-head-title) {
  font-size: 15px;
}
h2 {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}
h4 {
  margin: 18px 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}
.summary {
  margin-top: 12px;
  color: #1f2937;
  font-size: 14px;
  line-height: 1.75;
}
.detail-text {
  color: #1f2937;
  font-size: 14px;
  line-height: 1.75;
}
.sources-tag {
  margin-bottom: 8px;
}
.quote-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 14px;
  margin: 6px 0;
}
.quote-book {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}
.quote-text {
  font-size: 13.5px;
  color: #111827;
  line-height: 1.7;
}
</style>