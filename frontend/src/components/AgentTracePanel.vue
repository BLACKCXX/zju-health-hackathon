<template>
  <a-card class="soft-card" :bordered="false">
    <template #title>Agent Trace</template>
    <pre>{{ JSON.stringify(trace || {}, null, 2) }}</pre>
  </a-card>
</template>

<script setup lang="ts">
defineProps<{ trace: Record<string, unknown> | null }>()
</script>

<style scoped>
pre {
  max-height: 220px;
  margin: 0;
  overflow: auto;
  color: #475569;
  white-space: pre-wrap;
}
</style>
