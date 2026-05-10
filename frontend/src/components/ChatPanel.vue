<template>
  <section class="chat-panel soft-card">
    <div class="chat-header">
      <div>
        <h2>HealthPDF Agent</h2>
        <p>Router Agent → PDF Search Agent → Answer Agent</p>
      </div>
      <a-space>
        <a-tag color="cyan">PDF-RAG</a-tag>
        <a-tag color="blue">Hybrid Retrieval</a-tag>
        <a-button @click="$emit('clear')">清空对话</a-button>
      </a-space>
    </div>

    <div ref="scrollRef" class="messages">
      <div v-if="messages.length === 0" class="empty-state">
        <h3>可以开始提问</h3>
        <p>例如：我肩膀肿胀，可能是什么原因？</p>
      </div>
      <div v-for="(message, index) in messages" :key="index" class="message-row" :class="message.role">
        <div class="bubble">
          <div class="role">{{ message.role === 'user' ? 'You' : 'HealthPDF Agent' }}</div>
          <div class="markdown-text">{{ message.content }}</div>
        </div>
      </div>
      <div v-if="loading" class="message-row assistant">
        <div class="bubble loading-bubble">
          <a-spin size="small" />
          <span>Agent 正在规划检索并生成回答...</span>
        </div>
      </div>
    </div>

    <div class="sender">
      <a-textarea
        v-model:value="draft"
        :auto-size="{ minRows: 2, maxRows: 5 }"
        placeholder="请输入医学、健康、生物教材相关问题，例如：我肩膀肿胀，可能是什么原因？"
        @keydown.enter.exact.prevent="submit"
      />
      <a-button type="primary" size="large" :loading="loading" @click="submit">发送</a-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage } from '../types/api'

const props = defineProps<{
  messages: ChatMessage[]
  loading: boolean
}>()

const emit = defineEmits<{
  send: [message: string]
  clear: []
}>()

const draft = ref('')
const scrollRef = ref<HTMLElement | null>(null)

function submit() {
  const message = draft.value.trim()
  if (!message || props.loading) return
  draft.value = ''
  emit('send', message)
}

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  },
)
</script>

<style scoped>
.chat-panel {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.chat-header h2 {
  margin: 0;
  font-size: 22px;
}

.chat-header p {
  margin: 4px 0 0;
  color: #0f766e;
  font-weight: 700;
}

.messages {
  height: calc(100vh - 292px);
  min-height: 460px;
  overflow: auto;
  padding: 22px;
  background: linear-gradient(180deg, #f8fbff, #f4f8fb);
}

.empty-state {
  display: grid;
  height: 100%;
  place-content: center;
  text-align: center;
  color: #64748b;
}

.message-row {
  display: flex;
  margin-bottom: 18px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 76%;
  padding: 14px 16px;
  border-radius: 16px;
  background: white;
  box-shadow: 0 8px 20px rgba(31, 45, 61, 0.08);
}

.message-row.user .bubble {
  border-top-right-radius: 6px;
  background: #2563eb;
  color: white;
}

.message-row.assistant .bubble {
  border-top-left-radius: 6px;
  border: 1px solid #dbe7f1;
}

.role {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  opacity: 0.78;
}

.loading-bubble {
  display: flex;
  gap: 10px;
}

.sender {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid #e2e8f0;
  background: white;
}

.sender .ant-input {
  border-radius: 12px;
}
</style>
