<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="logo">H</div>
      <div>
        <h2>HealthPDF Agent</h2>
        <p>AI×大健康教材问答</p>
      </div>
    </div>

    <a-button type="primary" block size="large" @click="$emit('new-session')">
      新建会话
    </a-button>

    <a-card class="soft-card conversations" :bordered="false">
      <template #title>Conversations</template>
      <a-list size="small" :data-source="conversations">
        <template #renderItem="{ item }">
          <a-list-item class="conversation-item">{{ item }}</a-list-item>
        </template>
      </a-list>
    </a-card>

    <IndexStatusCard :status="status" />

    <a-card class="soft-card controls" :bordered="false">
      <template #title>构建索引</template>
      <a-form layout="vertical">
        <a-form-item label="Backend">
          <a-select v-model:value="localOptions.backend">
            <a-select-option value="tfidf">tfidf</a-select-option>
            <a-select-option value="hybrid">hybrid</a-select-option>
            <a-select-option value="embedding">embedding</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="max_pages_per_pdf">
          <a-slider v-model:value="localOptions.max_pages_per_pdf" :min="10" :max="300" :step="10" />
        </a-form-item>
        <a-space direction="vertical" class="switches">
          <a-switch v-model:checked="localOptions.debug" checked-children="debug" un-checked-children="debug" />
          <a-switch v-model:checked="localOptions.force" checked-children="force" un-checked-children="force" />
        </a-space>
        <a-space direction="vertical" class="actions">
          <a-button type="primary" block :loading="building" @click="$emit('build-index', localOptions)">
            构建索引
          </a-button>
          <a-button block @click="$emit('refresh-status')">检查状态</a-button>
        </a-space>
      </a-form>
    </a-card>

    <a-card class="soft-card controls" :bordered="false">
      <template #title>上传 PDF</template>
      <a-upload
        v-model:file-list="fileList"
        accept=".pdf"
        multiple
        :before-upload="beforeUpload"
      >
        <a-button block>选择 PDF</a-button>
      </a-upload>
      <a-button class="upload-action" block :loading="uploading" @click="submitUpload">
        上传到 uploads/
      </a-button>
    </a-card>
  </aside>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { UploadFile } from 'ant-design-vue/es/upload/interface'
import IndexStatusCard from './IndexStatusCard.vue'
import type { BuildIndexPayload, SystemStatus } from '../types/api'

defineProps<{
  status: SystemStatus | null
  building: boolean
  uploading: boolean
}>()

const emit = defineEmits<{
  'new-session': []
  'refresh-status': []
  'build-index': [payload: BuildIndexPayload]
  'upload-pdf': [files: File[]]
}>()

const conversations = ['当前演示会话', '症状解释示例', '传染病教材问答']

const localOptions = reactive<BuildIndexPayload>({
  backend: 'hybrid',
  force: true,
  debug: true,
  max_pages_per_pdf: 50,
  chunk_size: 1000,
  overlap: 150,
})

const fileList = ref<UploadFile[]>([])

function beforeUpload() {
  return false
}

function submitUpload() {
  const files = fileList.value
    .map((item) => item.originFileObj)
    .filter((item): item is File => Boolean(item))
  emit('upload-pdf', files)
}
</script>

<style scoped>
.sidebar {
  width: 320px;
  flex: 0 0 320px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, #0f766e, #2563eb);
  color: white;
  box-shadow: 0 16px 30px rgba(37, 99, 235, 0.22);
}

.logo {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 22px;
  font-weight: 800;
}

.brand h2 {
  margin: 0;
  font-size: 18px;
}

.brand p {
  margin: 4px 0 0;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
}

.conversations :deep(.ant-card-body) {
  padding-top: 0;
}

.conversation-item {
  padding: 8px 0 !important;
  color: #475569;
}

.switches,
.actions {
  width: 100%;
}

.upload-action {
  margin-top: 10px;
}
</style>
