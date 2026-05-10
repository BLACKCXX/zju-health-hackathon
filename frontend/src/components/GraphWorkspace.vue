<template>
  <section class="graph-workspace">
    <div class="graph-main">
      <a-tabs v-model:activeKey="activeTab" class="graph-tabs">
        <a-tab-pane key="single" tab="单本教材图谱">
          <a-card class="soft-card" :bordered="false">
            <div class="control-row">
              <a-select
                v-model:value="singleBookParams.textbook_id"
                placeholder="选择教材"
                style="width: 220px"
                :loading="loadingTextbooks"
              >
                <a-select-option v-for="tb in textbooks" :key="tb.textbook_id" :value="tb.textbook_id">
                  {{ tb.title || tb.filename }}
                </a-select-option>
              </a-select>
              <a-select
                v-model:value="singleBookParams.chapter_id"
                placeholder="选择章节（可选）"
                style="width: 200px"
                allowClear
              >
                <a-select-option v-for="ch in chapters" :key="ch.chapter_id" :value="ch.chapter_id">
                  {{ ch.title }}
                </a-select-option>
              </a-select>
              <a-button type="primary" :loading="loading" @click="buildSingleBook">
                生成单本图谱
              </a-button>
            </div>
          </a-card>
        </a-tab-pane>

        <a-tab-pane key="integrated" tab="跨教材整合图谱">
          <a-card class="soft-card" :bordered="false">
            <div class="control-row">
              <a-input
                v-model:value="integratedParams.topic"
                placeholder="输入主题，例如：炎症"
                style="width: 260px"
              />
              <a-select
                v-model:value="integratedParams.textbook_ids"
                mode="multiple"
                placeholder="选择教材范围（默认全部）"
                style="width: 300px"
                :loading="loadingTextbooks"
                allowClear
              >
                <a-select-option v-for="tb in textbooks" :key="tb.textbook_id" :value="tb.textbook_id">
                  {{ tb.title || tb.filename }}
                </a-select-option>
              </a-select>
              <a-button type="primary" :loading="loading" @click="buildIntegrated">
                生成跨教材整合图谱
              </a-button>
            </div>
          </a-card>
        </a-tab-pane>
      </a-tabs>

      <GraphCanvas
        :graph="graph"
        :search-keyword="searchKeyword"
        @node-click="selectNode"
      />

      <a-card class="soft-card" :bordered="false">
        <div class="control-row">
          <a-input
            v-model:value="instruction"
            placeholder="围绕当前图谱的修改指令，例如：补充炎症介质相关节点、把急性炎症和慢性炎症分开"
            allowClear
          />
          <a-button :disabled="!graph || !instruction.trim()" :loading="updating" @click="applyInstruction">
            应用指令
          </a-button>
        </div>
      </a-card>

      <a-card v-if="graph && activeTab === 'integrated'" class="soft-card" :bordered="false">
        <template #title>整合决策</template>
        <div v-if="graph.decisions?.length" class="decisions-list">
          <div v-for="d in graph.decisions" :key="d.decision_id" class="decision-item">
            <a-tag :color="d.action === 'merge' ? 'purple' : d.action === 'remove' ? 'red' : 'green'">
              {{ d.action }}
            </a-tag>
            <span class="decision-reason">{{ d.reason }}</span>
          </div>
        </div>
        <a-empty v-else description="暂无整合决策" />
      </a-card>
    </div>

    <aside class="graph-side">
      <ReportExporter :graph="graph" @export="handleExport" />
      <NodeDetailPanel :node="selectedNode" :detail="nodeDetail" />
      <FeedbackPanel
        :target-id="selectedNode?.id || null"
        :target-type="selectedNode ? 'node' : null"
        @feedback="handleFeedback"
      />
      <EvidencePanel
        :evidence="graph?.evidence || []"
        :filter-evidence-ids="selectedNode?.evidence_ids || []"
      />
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  buildIntegratedGraph,
  buildSingleBookGraph,
  exportReport,
  getNodeDetail,
  listTextbooks,
  sendFeedback,
  updateGraph,
} from '../api/client'
import type {
  GraphJSON,
  GraphNode,
  SingleBookGraphResponse,
  IntegratedGraphResponse,
} from '../types/api'
import type { TextbookSummary } from '../api/client'
import EvidencePanel from './EvidencePanel.vue'
import FeedbackPanel from './FeedbackPanel.vue'
import GraphCanvas from './GraphCanvas.vue'
import NodeDetailPanel from './NodeDetailPanel.vue'
import ReportExporter from './ReportExporter.vue'

const props = defineProps<{ initialTopic?: string }>()

const activeTab = ref<'single' | 'integrated'>('single')

const singleBookParams = ref({
  textbook_id: '',
  chapter_id: undefined as string | undefined,
})
const integratedParams = ref({
  topic: props.initialTopic || '',
  textbook_ids: [] as string[],
})
const instruction = ref('')
const searchKeyword = ref('')

const loading = ref(false)
const updating = ref(false)
const loadingTextbooks = ref(false)
const textbooks = ref<TextbookSummary[]>([])
const graph = ref<GraphJSON | null>(null)
const selectedNode = ref<GraphNode | null>(null)
const nodeDetail = ref<any | null>(null)

const chapters = computed(() => {
  const tb = textbooks.value.find((t) => t.textbook_id === singleBookParams.value.textbook_id)
  if (!tb) return []
  return (tb as any).chapters || []
})

async function loadTextbooks() {
  loadingTextbooks.value = true
  try {
    textbooks.value = await listTextbooks()
  } catch (error) {
    console.error('加载教材失败', error)
  } finally {
    loadingTextbooks.value = false
  }
}

async function buildSingleBook() {
  if (!singleBookParams.value.textbook_id) {
    message.warning('请先选择教材')
    return
  }
  loading.value = true
  try {
    const result: SingleBookGraphResponse = await buildSingleBookGraph(singleBookParams.value)
    graph.value = result.graph
    selectedNode.value = result.graph.nodes?.[0] || null
    nodeDetail.value = null
    message.success('单本教材图谱已生成')
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

async function buildIntegrated() {
  if (!integratedParams.value.topic.trim()) {
    message.warning('请输入主题')
    return
  }
  loading.value = true
  try {
    const result: IntegratedGraphResponse = await buildIntegratedGraph({
      topic: integratedParams.value.topic.trim(),
      textbook_ids: integratedParams.value.textbook_ids.length ? integratedParams.value.textbook_ids : undefined,
    })
    graph.value = result.graph
    selectedNode.value = result.graph.nodes?.[0] || null
    nodeDetail.value = null
    message.success('跨教材整合图谱已生成')
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

async function applyInstruction() {
  if (!graph.value || !instruction.value.trim()) return
  updating.value = true
  try {
    const result = await updateGraph(instruction.value.trim(), graph.value)
    graph.value = result.graph
    if (result.patch?.highlight_nodes?.length) {
      searchKeyword.value = ''
    }
    instruction.value = ''
    message.success('图谱已更新')
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    updating.value = false
  }
}

async function selectNode(node: GraphNode) {
  selectedNode.value = node
  nodeDetail.value = null
  if (!graph.value) return
  try {
    nodeDetail.value = await getNodeDetail(node.id, node.name, graph.value)
  } catch (error) {
    message.error((error as Error).message)
  }
}

async function handleFeedback(action: string, comment: string) {
  if (!graph.value || !selectedNode.value) return
  try {
    const result = await sendFeedback({
      action: action as any,
      target_type: 'node',
      target_id: selectedNode.value.id,
      comment,
      graph: graph.value,
    })
    graph.value = result.updated_graph
    message.success('教师反馈已记录')
  } catch (error) {
    message.error((error as Error).message)
  }
}

async function handleExport() {
  if (!graph.value) return
  try {
    const result = await exportReport(graph.value)
    const blob = new Blob([result.markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = result.filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    message.error((error as Error).message)
  }
}

loadTextbooks()
</script>

<style scoped>
.graph-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 18px;
}
.graph-main,
.graph-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.graph-tabs {
  background: #fff;
  border-radius: 12px;
}
.control-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.decisions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.decision-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.decision-reason {
  color: #64748b;
  font-size: 13px;
}
</style>