<template>
  <section class="textbook-manager">
    <div class="section-header">
      <h2>教材管理区</h2>
      <a-tag v-if="ragStatus" :color="ragStatus.indexed ? 'blue' : 'orange'">
        {{ ragStatus.indexed ? '已索引' : '未索引' }}
      </a-tag>
    </div>

    <!-- Upload Area -->
    <a-card class="soft-card" :bordered="false" title="上传教材">
      <div
        class="upload-zone"
        :class="{ 'drag-over': isDragOver }"
        @dragover.prevent="isDragOver = true"
        @dragleave="isDragOver = false"
        @drop.prevent="handleDrop"
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept=".pdf,.md,.txt,.docx"
          style="display: none"
          @change="handleFileSelect"
        />
        <label for="file-input" class="upload-label">
          <cloud-upload-outlined style="font-size: 36px; color: #2563eb" />
          <p>拖拽文件到此处，或 <span class="link">点击选择</span></p>
          <p class="hint">支持 PDF、Markdown、TXT、Word .docx 格式</p>
        </label>
      </div>

      <div v-if="uploadingCount > 0" class="upload-progress">
        <a-progress :percent="uploadProgress" status="active" />
        正在上传 {{ uploadingCount }} 个文件...
      </div>
    </a-card>

    <!-- File List -->
    <a-card class="soft-card" :bordered="false" title="教材列表">
      <template #extra>
        <a-space>
          <a-button size="small" @click="refreshList" :loading="loadingList">
            <reload-outlined /> 刷新
          </a-button>
          <a-button
            size="small"
            type="primary"
            @click="parseAll"
            :loading="parsing"
            :disabled="textbooks.length === 0"
          >
            批量解析并索引
          </a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns"
        :data-source="textbooks"
        :loading="loadingList"
        row-key="textbook_id"
        size="small"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.parse_status)">
              {{ getStatusText(record.parse_status) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space size="small">
              <a-button
                size="small"
                type="primary"
                @click="parseAndIndex(record)"
                :loading="parsing"
              >
                解析并索引
              </a-button>
              <a-button
                size="small"
                @click="viewChapters(record)"
                :disabled="record.parse_status !== 'completed'"
              >
                查看章节
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Index Status -->
    <a-card v-if="ragStatus" class="soft-card" :bordered="false" title="索引状态">
      <a-descriptions :column="2" size="small">
        <a-descriptions-item label="索引状态">
          <a-tag :color="ragStatus.indexed ? 'green' : 'red'">
            {{ ragStatus.indexed ? '已构建' : '未构建' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="教材数">{{ ragStatus.textbook_count }}</a-descriptions-item>
        <a-descriptions-item label="Chunk 数">{{ ragStatus.chunk_count }}</a-descriptions-item>
        <a-descriptions-item label="Embedding">{{ ragStatus.embedding_model || '-' }}</a-descriptions-item>
        <a-descriptions-item label="检索后端">{{ ragStatus.backend }}</a-descriptions-item>
        <a-descriptions-item label="Fallback">{{ ragStatus.fallback_backend || '无' }}</a-descriptions-item>
        <a-descriptions-item label="创建时间">{{ ragStatus.created_at || '-' }}</a-descriptions-item>
      </a-descriptions>
    </a-card>

    <!-- Chapter Detail Drawer -->
    <a-drawer
      v-model:open="drawerVisible"
      :title="drawerTitle"
      placement="right"
      :width="520"
      :loading="drawerLoading"
    >
      <template v-if="!drawerLoading && selectedTextbook">
        <h3>{{ selectedTextbook.title }}</h3>
        <a-descriptions :column="2" size="small" style="margin-bottom: 16px">
          <a-descriptions-item label="文件名">{{ selectedTextbook.filename }}</a-descriptions-item>
          <a-descriptions-item label="格式">{{ selectedTextbook.format }}</a-descriptions-item>
          <a-descriptions-item label="总页数">{{ selectedTextbook.total_pages || chapterDetail?.total_pages || 0 }}</a-descriptions-item>
          <a-descriptions-item label="总字数">{{ selectedTextbook.total_chars || chapterDetail?.total_chars || 0 }}</a-descriptions-item>
        </a-descriptions>

        <a-divider>章节列表</a-divider>
        <template v-if="chapterDetail?.chapters?.length">
          <a-collapse :bordered="false">
            <a-collapse-panel
              v-for="chapter in chapterDetail.chapters"
              :key="chapter.chapter_id"
              :header="`${chapter.title} (页 ${chapter.page_start}-${chapter.page_end})`"
            >
              <p class="chapter-preview">{{ (chapter.content || '').substring(0, 300) }}...</p>
              <div class="chapter-meta">
                <span>字数: {{ chapter.char_count || 0 }}</span>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </template>
        <p v-else class="no-data">该教材暂无章节结构</p>
      </template>
      <div v-if="drawerLoading" class="loading-container">
        <a-spin tip="加载中..." />
      </div>
    </a-drawer>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { CloudUploadOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import {
  listTextbooks,
  uploadTextbooks,
  parseTextbooks,
  getTextbookDetail,
  getRAGStatus,
  type TextbookSummary,
} from '../api/client'

interface Chapter {
  chapter_id: string
  title: string
  page_start: number
  page_end: number
  content: string
  char_count: number
}

interface TextbookDetailResponse {
  textbook_id: string
  filename: string
  title: string
  format: string
  total_pages: number
  total_chars: number
  chapters: Chapter[]
  parse_status: string
  error: string
}

const textbooks = ref<TextbookSummary[]>([])
const ragStatus = ref<{
  indexed: boolean
  textbook_count: number
  chunk_count: number
  embedding_model: string
  backend: string
  fallback_backend: string
  created_at: string
} | null>(null)
const loadingList = ref(false)
const uploadingCount = ref(0)
const uploadProgress = ref(0)
const parsing = ref(false)
const isDragOver = ref(false)
const drawerVisible = ref(false)
const drawerLoading = ref(false)
const selectedTextbookId = ref<string | null>(null)
const chapterDetail = ref<TextbookDetailResponse | null>(null)

// Derive the textbook displayed in drawer from chapterDetail (loaded from API)
const selectedTextbook = computed(() => chapterDetail.value)

const columns = [
  { title: '文件名', dataIndex: 'filename', key: 'filename' },
  { title: '格式', dataIndex: 'format', key: 'format', width: 70 },
  { title: '页数', dataIndex: 'total_pages', key: 'total_pages', width: 70 },
  { title: '字数', dataIndex: 'total_chars', key: 'total_chars', width: 80 },
  { title: '章节数', dataIndex: 'chapter_count', key: 'chapter_count', width: 80 },
  { title: '状态', dataIndex: 'parse_status', key: 'status', width: 100 },
  { title: '操作', key: 'actions', width: 180 },
]

const drawerTitle = computed(() => {
  if (!selectedTextbookId.value) return '教材章节结构'
  const tb = textbooks.value.find(t => t.textbook_id === selectedTextbookId.value)
  return tb ? `${tb.title} - 章节结构` : '教材章节结构'
})

function getStatusColor(status: string) {
  const map: Record<string, string> = {
    pending: 'default',
    parsing: 'processing',
    completed: 'success',
    failed: 'error',
  }
  return map[status] || 'default'
}

function getStatusText(status: string) {
  const map: Record<string, string> = {
    pending: '等待解析',
    parsing: '解析中',
    completed: '已解析并索引',
    failed: '失败',
  }
  return map[status] || status
}

async function refreshList() {
  loadingList.value = true
  try {
    textbooks.value = await listTextbooks()
    ragStatus.value = await getRAGStatus()
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    loadingList.value = false
  }
}

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  await uploadFiles(Array.from(input.files))
}

async function handleDrop(event: DragEvent) {
  isDragOver.value = false
  const files = event.dataTransfer?.files
  if (!files?.length) return
  await uploadFiles(Array.from(files))
}

async function uploadFiles(files: File[]) {
  uploadingCount.value = files.length
  uploadProgress.value = 0
  try {
    const result = await uploadTextbooks(files)
    if (result.success) {
      message.success(result.message)
      await refreshList()
    } else {
      message.warning(result.message)
    }
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    uploadingCount.value = 0
  }
}

async function parseAndIndex(record: TextbookSummary) {
  parsing.value = true
  try {
    const result = await parseTextbooks([record.filename])
    if (result.success) {
      message.success(`解析成功：${record.filename}`)
      await refreshList()
    } else {
      message.error(result.textbooks[0]?.error || '解析失败')
    }
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    parsing.value = false
  }
}

async function parseAll() {
  const pendingFiles = textbooks.value.filter(t => t.parse_status === 'pending' || t.parse_status === 'failed')
  if (pendingFiles.length === 0) {
    message.info('没有需要解析的教材')
    return
  }
  parsing.value = true
  try {
    const result = await parseTextbooks(pendingFiles.map(t => t.filename))
    if (result.success) {
      message.success(`成功解析 ${result.textbooks.length} 本教材并自动构建索引`)
    } else {
      message.error(result.message ?? '解析并索引完成')
    }
    await refreshList()
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    parsing.value = false
  }
}

async function viewChapters(record: TextbookSummary) {
  // Set loading state
  drawerLoading.value = true
  chapterDetail.value = null
  selectedTextbookId.value = record.textbook_id

  // Always open drawer first, then load data
  drawerVisible.value = true

  try {
    // Fetch specific textbook by its textbook_id
    const detail = await getTextbookDetail(record.textbook_id)
    if (detail) {
      chapterDetail.value = detail
      // Update the textbooks list with fresh data
      const idx = textbooks.value.findIndex(t => t.textbook_id === record.textbook_id)
      if (idx >= 0) {
        textbooks.value[idx] = {
          ...textbooks.value[idx],
          total_pages: detail.total_pages,
          total_chars: detail.total_chars,
          chapter_count: detail.chapters?.length || 0,
          parse_status: detail.parse_status,
        }
      }
    }
  } catch (error) {
    message.error((error as Error).message)
    chapterDetail.value = null
  } finally {
    drawerLoading.value = false
  }
}

onMounted(refreshList)
</script>

<style scoped>
.textbook-manager {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.section-header h2 {
  margin: 0;
  font-size: 18px;
  color: #102033;
}

.upload-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  transition: border-color 0.3s;
  cursor: pointer;
}

.upload-zone.drag-over {
  border-color: #2563eb;
  background: #f0f7ff;
}

.upload-label {
  cursor: pointer;
  display: block;
}

.upload-label p {
  margin: 8px 0 0;
  color: #64748b;
}

.upload-label .link {
  color: #2563eb;
  text-decoration: underline;
}

.upload-label .hint {
  font-size: 12px;
  color: #94a3b8;
}

.upload-progress {
  margin-top: 16px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 6px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.no-data {
  color: #94a3b8;
  text-align: center;
  padding: 20px;
}

.chapter-preview {
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
  background: #f8fafc;
  padding: 8px;
  border-radius: 4px;
}

.chapter-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}
</style>
