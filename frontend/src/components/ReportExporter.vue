<template>
  <a-button type="primary" :disabled="!graph" @click="$emit('export')">导出 Markdown 报告</a-button>
</template>

<script setup lang="ts">
import type { GraphJSON } from '../types/graph'
defineProps<{ graph: GraphJSON | null }>()
defineEmits<{ export: [] }>()
</script>
