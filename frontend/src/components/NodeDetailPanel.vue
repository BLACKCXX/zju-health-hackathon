<template>
  <a-card class="soft-card detail-card" :bordered="false">
    <template #title>节点详情</template>
    <a-empty v-if="!node" description="点击图谱节点查看详情" />
    <div v-else>
      <h2>{{ node.name }}</h2>
      <a-space wrap>
        <a-tag color="blue">{{ node.type }}</a-tag>
        <a-tag color="green">置信度 {{ ((node.confidence || 0) * 100).toFixed(0) }}%</a-tag>
        <a-tag v-if="node.chapter" color="purple">{{ node.chapter }}</a-tag>
        <a-tag v-if="node.page">第 {{ node.page }} 页</a-tag>
      </a-space>
      <p v-if="node.summary" class="summary">{{ node.summary }}</p>
      <a-divider />
      <h4>详细解释</h4>
      <p>{{ detail?.detail || '点击节点后由后端基于证据生成详细解释。' }}</p>
      <template v-if="node.book_sources?.length">
        <h4>来源教材</h4>
        <a-tag v-for="book in node.book_sources" :key="book" color="cyan">{{ book }}</a-tag>
      </template>
      <template v-if="detail?.overlap_analysis">
        <h4>跨教材重复分析</h4>
        <p>{{ detail.overlap_analysis }}</p>
      </template>
      <template v-if="detail?.complement_analysis">
        <h4>跨教材互补分析</h4>
        <p>{{ detail.complement_analysis }}</p>
      </template>
      <h4>证据引用</h4>
      <a-list :data-source="detail?.sources || []" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <span>{{ item.book }} · 第 {{ item.page }} 页</span>
            <p class="quote">{{ item.quote }}</p>
          </a-list-item>
        </template>
      </a-list>
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
.summary {
  margin-top: 12px;
  color: #475569;
  line-height: 1.6;
}
h2 {
  margin: 0 0 10px;
  font-size: 18px;
}
h4 {
  margin: 16px 0 8px;
  font-size: 13px;
  color: #64748b;
}
.quote {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
}
</style>