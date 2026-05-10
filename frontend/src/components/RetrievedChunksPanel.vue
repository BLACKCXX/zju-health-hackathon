<template>
  <a-card class="soft-card chunks-card" :bordered="false">
    <template #title>教材引用片段</template>
    <a-empty v-if="chunks.length === 0" description="暂无检索片段" />
    <a-collapse v-else ghost>
      <a-collapse-panel
        v-for="(chunk, index) in chunks"
        :key="`${chunk.source_file}-${chunk.page}-${index}`"
        :header="`#${index + 1} ${chunk.source_file} · 第 ${chunk.page} 页`"
      >
        <div class="chunk-meta">
          <a-tag color="green">score {{ (chunk.score || 0).toFixed(4) }}</a-tag>
          <a-tag color="blue">{{ chunk.match_type || 'unknown' }}</a-tag>
        </div>
        <p class="chunk-text">{{ chunk.text }}</p>
      </a-collapse-panel>
    </a-collapse>
  </a-card>
</template>

<script setup lang="ts">
import type { RetrievedChunk } from '../types/api'

defineProps<{
  chunks: RetrievedChunk[]
}>()
</script>

<style scoped>
.chunks-card {
  max-height: 360px;
  overflow: auto;
}

.chunk-meta {
  margin-bottom: 8px;
}

.chunk-text {
  max-height: 190px;
  margin: 0;
  overflow: auto;
  color: #475569;
  line-height: 1.65;
  white-space: pre-wrap;
}
</style>
