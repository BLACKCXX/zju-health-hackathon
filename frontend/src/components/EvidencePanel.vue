<template>
  <a-card class="soft-card" :bordered="false">
    <template #title>证据来源</template>
    <a-empty v-if="filteredEvidence.length === 0" description="暂无证据" />
    <a-collapse v-else ghost>
      <a-collapse-panel
        v-for="item in filteredEvidence"
        :key="item.evidence_id"
        :header="`${item.textbook} · 第 ${item.page} 页`"
      >
        <p class="quote-text">{{ item.quote }}</p>
        <a-tag>{{ item.chapter }}</a-tag>
      </a-collapse-panel>
    </a-collapse>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { GraphEvidence } from '../types/graph'

const props = defineProps<{
  evidence: GraphEvidence[]
  filterEvidenceIds?: string[]
}>()

const filteredEvidence = computed(() => {
  if (!props.filterEvidenceIds?.length) return props.evidence
  return props.evidence.filter((e) => props.filterEvidenceIds!.includes(e.evidence_id))
})
</script>

<style scoped>
.quote-text {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}
</style>