<template>
  <a-config-provider :theme="theme">
    <main class="app-shell">
      <header class="hero soft-card">
        <div>
          <h1>HealthPDF Agent</h1>
          <p class="subtitle">面向大健康教材的多 Agent 问答系统</p>
          <p class="flow">Router Agent → PDF Search Agent → Answer Agent</p>
        </div>
        <a-alert
          class="safety"
          type="success"
          show-icon
          message="本系统仅用于学习与信息辅助理解，不提供医学诊断，不能替代医生建议。"
        />
      </header>

      <section class="workspace">
        <Sidebar
          :status="status"
          :building="building"
          :uploading="uploading"
          @new-session="clearConversation"
          @refresh-status="refreshStatus"
          @build-index="handleBuildIndex"
          @upload-pdf="handleUploadPdf"
        />
        <ChatPanel
          :messages="messages"
          :loading="chatLoading"
          @send="handleSend"
          @clear="clearConversation"
        />
        <aside class="insights">
          <AgentRoutePanel :route-info="routeInfo" />
          <RetrievedChunksPanel :chunks="retrievedChunks" />
          <ChartsPanel :chunks="retrievedChunks" />
        </aside>
      </section>
    </main>
  </a-config-provider>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { message as antMessage, theme as antTheme } from 'ant-design-vue'
import AgentRoutePanel from './components/AgentRoutePanel.vue'
import ChartsPanel from './components/ChartsPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import RetrievedChunksPanel from './components/RetrievedChunksPanel.vue'
import Sidebar from './components/Sidebar.vue'
import { buildIndex, getStatus, sendChatMessage, uploadPdf } from './api/client'
import type { BuildIndexPayload, ChatMessage, RetrievedChunk, RouteInfo, SystemStatus } from './types/api'

const theme = {
  algorithm: antTheme.defaultAlgorithm,
  token: {
    colorPrimary: '#2563eb',
    borderRadius: 12,
    fontFamily: 'Inter, "Microsoft YaHei", sans-serif',
  },
}

const status = ref<SystemStatus | null>(null)
const messages = ref<ChatMessage[]>([])
const routeInfo = ref<RouteInfo | null>(null)
const retrievedChunks = ref<RetrievedChunk[]>([])
const chatLoading = ref(false)
const building = ref(false)
const uploading = ref(false)

async function refreshStatus() {
  try {
    status.value = await getStatus()
  } catch (error) {
    antMessage.error((error as Error).message)
  }
}

async function handleSend(content: string) {
  const userMessage: ChatMessage = { role: 'user', content }
  messages.value = [...messages.value, userMessage]
  chatLoading.value = true
  try {
    const response = await sendChatMessage({
      message: content,
      history: messages.value.slice(0, -1),
      top_k: 5,
      force_pdf_search: true,
    })
    messages.value = [...messages.value, { role: 'assistant', content: response.answer }]
    routeInfo.value = response.route_info
    retrievedChunks.value = response.retrieved_chunks || []
  } catch (error) {
    const fallback = (error as Error).message || '后端服务不可用，请确认 FastAPI 已启动'
    messages.value = [...messages.value, { role: 'assistant', content: fallback }]
    antMessage.error(fallback)
  } finally {
    chatLoading.value = false
  }
}

async function handleBuildIndex(payload: BuildIndexPayload) {
  building.value = true
  try {
    const result = await buildIndex(payload)
    if (result.success) {
      antMessage.success(result.warning ? `${result.message} ${result.warning}` : result.message)
    } else {
      antMessage.warning(result.message)
    }
    await refreshStatus()
  } catch (error) {
    antMessage.error((error as Error).message)
  } finally {
    building.value = false
  }
}

async function handleUploadPdf(files: File[]) {
  if (files.length === 0) {
    antMessage.warning('请先选择 PDF 文件')
    return
  }
  uploading.value = true
  try {
    const result = await uploadPdf(files)
    result.success ? antMessage.success(result.message) : antMessage.warning(result.message)
    await refreshStatus()
  } catch (error) {
    antMessage.error((error as Error).message)
  } finally {
    uploading.value = false
  }
}

function clearConversation() {
  messages.value = []
  routeInfo.value = null
  retrievedChunks.value = []
}

onMounted(refreshStatus)
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: 22px;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 22px 26px;
  background: linear-gradient(135deg, #ffffff 0%, #eef7f4 55%, #edf4ff 100%);
}

.hero h1 {
  margin: 0;
  color: #102033;
  font-size: 34px;
  line-height: 1.1;
}

.subtitle {
  margin: 8px 0 4px;
  color: #31506f;
  font-size: 16px;
}

.flow {
  margin: 0;
  color: #0f766e;
  font-weight: 800;
}

.safety {
  max-width: 520px;
  border-radius: 12px;
}

.workspace {
  display: flex;
  align-items: stretch;
  gap: 18px;
}

.insights {
  width: 390px;
  flex: 0 0 390px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

@media (max-width: 1280px) {
  body {
    min-width: 0;
  }

  .workspace {
    flex-direction: column;
  }

  .insights,
  :deep(.sidebar) {
    width: 100%;
    flex-basis: auto;
  }
}
</style>
