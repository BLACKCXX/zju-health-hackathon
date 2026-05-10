<template>
  <a-config-provider :theme="theme">
    <LayoutShell :mode="mode" @update:mode="mode = $event">
      <TextbookManager v-if="mode === 'textbook'" />
      <AskMode
        v-else-if="mode === 'ask'"
        :status="status"
        @build-graph="openGraphFromFlashcard"
      />
      <GraphWorkspace v-else :initial-topic="graphTopic" />
    </LayoutShell>
  </a-config-provider>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { message, theme as antTheme } from 'ant-design-vue'
import { getStatus } from './api/client'
import AskMode from './components/AskMode.vue'
import GraphWorkspace from './components/GraphWorkspace.vue'
import LayoutShell from './components/LayoutShell.vue'
import TextbookManager from './components/TextbookManager.vue'
import type { SystemStatus } from './types/api'

const theme = {
  algorithm: antTheme.defaultAlgorithm,
  token: {
    colorPrimary: '#2563eb',
    borderRadius: 12,
    fontFamily: 'Inter, "Microsoft YaHei", sans-serif',
  },
}

const mode = ref<'ask' | 'graph' | 'textbook'>('ask')
const graphTopic = ref('')
const status = ref<SystemStatus | null>(null)

async function refreshStatus() {
  try {
    status.value = await getStatus()
  } catch (error) {
    message.error((error as Error).message)
  }
}

function openGraphFromFlashcard(topic: string) {
  graphTopic.value = topic
  mode.value = 'graph'
}

onMounted(refreshStatus)
</script>