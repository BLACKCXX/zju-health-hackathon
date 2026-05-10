<template>
  <a-card class="soft-card graph-card" :bordered="false">
    <template #title>
      <span>知识图谱</span>
      <a-input
        v-model:value="searchKw"
        placeholder="搜索节点..."
        size="small"
        style="width: 160px; margin-left: 12px"
        @input="onSearch"
      />
    </template>
    <a-empty v-if="!graph || graph.nodes.length === 0" description="请选择教材和主题生成图谱" />
    <VChart v-else class="graph" :option="option" autoresize @click="handleClick" />
  </a-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { GraphJSON, GraphNode } from '../types/graph'

use([GraphChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  graph: GraphJSON | null
  searchKeyword?: string
}>()

const emit = defineEmits<{
  nodeClick: [node: GraphNode]
}>()

const searchKw = ref('')

const colorMap: Record<string, string> = {
  concept: '#2563eb',
  mechanism: '#7c3aed',
  disease: '#dc2626',
  symptom: '#f97316',
  diagnosis: '#0891b2',
  treatment: '#16a34a',
  risk_factor: '#ca8a04',
  complication: '#be123c',
  prevention: '#059669',
  book_specific: '#64748b',
}

const typeSizeMap: Record<string, number> = {
  concept: 60,
  mechanism: 55,
  disease: 65,
  symptom: 50,
  diagnosis: 55,
  treatment: 60,
  risk_factor: 50,
  complication: 55,
  prevention: 50,
  book_specific: 45,
}

function getNodeSize(node: GraphNode): number {
  const base = typeSizeMap[node.type] || 45
  if (node.level === 0) return base * 1.4
  if (node.status === 'added') return base * 1.2
  const freq = node.frequency || 1
  return base * (0.8 + Math.min(freq * 0.1, 0.4))
}

function getNodeColor(node: GraphNode): string {
  if (node.status === 'highlighted') return '#f59e0b'
  if (node.status === 'added') return '#f97316'
  if (node.status === 'updated') return '#3b82f6'
  return colorMap[node.type] || '#64748b'
}

const highlightedIds = computed(() => {
  const kw = (props.searchKeyword || searchKw.value || '').trim().toLowerCase()
  if (!kw || !props.graph) return new Set<string>()
  const ids = new Set<string>()
  for (const n of props.graph.nodes) {
    if (n.name.toLowerCase().includes(kw) || n.summary?.toLowerCase().includes(kw)) {
      ids.add(n.id)
    }
  }
  return ids
})

const option = computed(() => {
  const graph = props.graph
  if (!graph) return {}

  const nodes = graph.nodes.filter((n) => n.status !== 'deleted')
  const edges = graph.edges.filter((e) => e.status !== 'deleted')
  const hl = highlightedIds.value

  return {
    tooltip: {
      formatter: (p: any) => {
        const n = p.data as GraphNode
        if (!n) return p.data?.name || ''
        return `<b>${n.name}</b><br/><span style="color:#64748b">${n.type} | 置信度 ${(n.confidence * 100).toFixed(0)}%</span><br/>${n.summary || ''}`
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        label: { show: true, formatter: '{b}', fontSize: 12, color: '#1e293b' },
        force: { repulsion: 400, edgeLength: 130, gravity: 0.2 },
        edgeSymbol: ['circle', 'arrow'],
        data: nodes.map((node) => ({
          ...node,
          id: node.id,
          name: node.name,
          symbolSize: getNodeSize(node),
          itemStyle: {
            color: hl.has(node.id) ? '#f59e0b' : getNodeColor(node),
            borderColor: hl.has(node.id) ? '#f97316' : '#ffffff',
            borderWidth: hl.has(node.id) ? 3 : 2,
          },
        })),
        links: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
          label: {
            show: true,
            formatter: edge.label,
            fontSize: 11,
            color: '#64748b',
          },
          lineStyle: {
            color: edge.status === 'added' ? '#f59e0b' : edge.status === 'updated' ? '#3b82f6' : '#94a3b8',
            width: edge.status === 'added' ? 2 : 1.5,
            curveness: 0.1,
          },
        })),
      },
    ],
  }
})

function onSearch() {
  // Trigger highlight re-computation via reactive update
}

function handleClick(params: any) {
  if (params.dataType === 'node') {
    emit('nodeClick', params.data as GraphNode)
  }
}
</script>

<style scoped>
.graph-card {
  min-height: 620px;
}
.graph {
  width: 100%;
  height: 560px;
}
</style>