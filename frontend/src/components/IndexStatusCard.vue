<template>
  <a-card class="soft-card status-card" :bordered="false">
    <template #title>
      <span>系统状态</span>
    </template>
    <a-skeleton v-if="!status" active :paragraph="{ rows: 5 }" />
    <div v-else class="status-grid">
      <div class="status-row">
        <span>API</span>
        <a-tag :color="status.api_configured ? 'green' : 'red'">
          {{ status.api_configured ? '已配置' : '未配置' }}
        </a-tag>
      </div>
      <div class="status-row">
        <span>Answer 模型</span>
        <b>{{ status.answer_model || '-' }}</b>
      </div>
      <div class="status-row">
        <span>Embedding</span>
        <b>{{ status.embedding_model || '-' }}</b>
      </div>
      <div class="status-row">
        <span>PDF 数量</span>
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
        <span>检索缓存</span>
        <b>Emb {{ status.has_embedding ? 'on' : 'off' }} / TF-IDF {{ status.has_tfidf ? 'on' : 'off' }}</b>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { SystemStatus } from '../types/api'

defineProps<{
  status: SystemStatus | null
}>()
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
  max-width: 170px;
  color: #102033;
  text-align: right;
  word-break: break-word;
}
</style>
