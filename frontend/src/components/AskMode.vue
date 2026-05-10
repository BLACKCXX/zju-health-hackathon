<template>
  <section class="ask-grid">
    <div class="main-col">
      <a-card class="soft-card" :bordered="false">
        <template #title>知识小回答</template>
        <a-input-search
          v-model:value="question"
          size="large"
          enter-button="提问"
          :loading="loading"
          placeholder="请输入教材相关问题，例如：什么是高血压？"
          @search="submit"
        />
      </a-card>
      <KnowledgeAnswer :answer="answer" />
    </div>
    <aside class="side-col">
      <IndexStatusCard :status="status" />
      <FlashcardPanel :flashcards="answer?.flashcards || []" @build-graph="$emit('build-graph', $event)" />
      <AgentTracePanel :trace="answer?.agent_trace || null" />
    </aside>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { askQuestion } from '../api/client'
import type { AskResponse, SystemStatus } from '../types/api'
import AgentTracePanel from './AgentTracePanel.vue'
import FlashcardPanel from './FlashcardPanel.vue'
import IndexStatusCard from './IndexStatusCard.vue'
import KnowledgeAnswer from './KnowledgeAnswer.vue'

defineProps<{ status: SystemStatus | null }>()
defineEmits<{ 'build-graph': [topic: string] }>()

const question = ref('')
const loading = ref(false)
const answer = ref<AskResponse | null>(null)

async function submit() {
  if (!question.value.trim()) return
  loading.value = true
  try {
    answer.value = await askQuestion(question.value.trim(), 8)
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ask-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 390px;
  gap: 18px;
}
.main-col,
.side-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
