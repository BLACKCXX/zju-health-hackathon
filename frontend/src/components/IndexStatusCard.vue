<template>
  <a-card class="soft-card status-card" :bordered="false">
    <template #title>系统状态</template>
    <a-skeleton v-if="!status" active :paragraph="{ rows: 5 }" />
    <div v-else class="status-grid">
      <div class="status-row">
        <span>API</span>
        <a-tag :color="status.api_configured ? 'green' : 'red'">
          {{ status.api_configured ? '已配置' : '未配置' }}
        </a-tag>
      </div>
      <div class="status-row">
        <span>教材 PDF</span>
        <b>{{ status.pdf_count }}</b>
      </div>
      <div class="status-row">
        <span>索引</span>
        <a-tag :color="status.index_exists ? 'blue' : 'orange'">
          {{ status.index_exists ? '已构建' : '未构建' }}
        </a-tag>
      </div>
      <div class="status-row">
        <span>Chunk</span>
        <b>{{ status.chunk_count || 0 }}</b>
      </div>
      <div class="status-row">
        <span>检索后端</span>
        <b>{{ status.retrieval_backend }}</b>
      </div>
      <div class="status-row">
        <span>默认模型</span>
        <b>{{ status.models?.default || '-' }}</b>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { SystemStatus } from '../types/api'
defineProps<{ status: SystemStatus | null }>()
</script>

<style scoped>
.status-card {
  overflow: hidden;
}
.status-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.status-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #475569;
  font-size: 13px;
}
.status-row b {
  max-width: 190px;
  color: #102033;
  text-align: right;
  word-break: break-word;
}
</style>
