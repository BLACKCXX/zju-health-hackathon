<template>
  <a-card class="soft-card sankey-card" :bordered="false">
    <template #title>{{ title }}</template>
    <a-empty v-if="!hasEvidence" description="暂无 evidence，生成图谱后可查看证据流。" />
    <VChart v-else class="sankey-chart" :option="option" autoresize />
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { SankeyChart } from 'echarts/charts'
import { TooltipComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { GraphJSON, GraphNode } from '../types/graph'

use([SankeyChart, TooltipComponent, TitleComponent, CanvasRenderer])

const props = defineProps<{
  graph: GraphJSON | null
  title?: string
}>()

type SankeyNode = {
  name: string
  displayName: string
  fullName: string
  layer: '教材' | '章节' | '节点类型'
}

type SankeyLink = {
  source: string
  target: string
  value: number
}

const title = computed(() => props.title || 'RAG 证据流：教材 → 章节 → 节点类型')
const evidenceList = computed(() => props.graph?.evidence || [])
const graphNodes = computed(() => (props.graph?.nodes || []).filter(node => node.status !== 'deleted'))
const hasEvidence = computed(() => evidenceList.value.length > 0)

function getEvidenceBook(evidence: any): string {
  return String(evidence.textbook || evidence.book || evidence.source_file || '未知教材')
}

function getEvidenceChapter(evidence: any): string {
  return String(evidence.chapter || '未识别章节')
}

function shortName(name: string, maxLength = 18): string {
  return name.length > maxLength ? `${name.slice(0, maxLength)}...` : name
}

function nodeKey(layer: string, name: string): string {
  return `${layer}::${name}`
}

function addSankeyNode(nodes: Map<string, SankeyNode>, layer: SankeyNode['layer'], name: string) {
  const key = nodeKey(layer, name)
  if (!nodes.has(key)) {
    nodes.set(key, {
      name: key,
      displayName: shortName(name),
      fullName: name,
      layer,
    })
  }
  return key
}

function addLink(links: Map<string, SankeyLink>, source: string, target: string, value = 1) {
  const key = `${source}=>${target}`
  const existing = links.get(key)
  if (existing) {
    existing.value += value
  } else {
    links.set(key, { source, target, value })
  }
}

function getLinkedNodes(evidenceId: string): GraphNode[] {
  if (!evidenceId) return []
  return graphNodes.value.filter(node => (node.evidence_ids || []).includes(evidenceId))
}

const sankeyData = computed(() => {
  const nodes = new Map<string, SankeyNode>()
  const links = new Map<string, SankeyLink>()

  for (const evidence of evidenceList.value as any[]) {
    const evidenceId = String(evidence.evidence_id || '')
    const book = getEvidenceBook(evidence)
    const chapter = getEvidenceChapter(evidence)
    const bookNode = addSankeyNode(nodes, '教材', book)
    const chapterNode = addSankeyNode(nodes, '章节', chapter)

    addLink(links, bookNode, chapterNode, 1)

    const linkedNodes = getLinkedNodes(evidenceId)
    if (linkedNodes.length === 0) {
      const unlinkedNode = addSankeyNode(nodes, '节点类型', '未绑定节点')
      addLink(links, chapterNode, unlinkedNode, 1)
      continue
    }

    for (const node of linkedNodes) {
      const typeName = node.type || 'unlinked_evidence'
      const typeNode = addSankeyNode(nodes, '节点类型', typeName)
      addLink(links, chapterNode, typeNode, 1)
    }
  }

  return {
    nodes: Array.from(nodes.values()),
    links: Array.from(links.values()),
  }
})

const option = computed(() => ({
  title: {
    text: 'RAG 证据流：教材 → 章节 → 节点类型',
    left: 8,
    top: 4,
    textStyle: {
      color: '#111827',
      fontSize: 14,
      fontWeight: 600,
    },
  },
  tooltip: {
    trigger: 'item',
    backgroundColor: '#fff',
    borderColor: '#d1d5db',
    borderWidth: 1,
    textStyle: {
      color: '#111827',
      fontSize: 14,
      lineHeight: 22,
    },
    formatter: (params: any) => {
      if (params.dataType === 'edge') {
        const source = sankeyData.value.nodes.find(node => node.name === params.data.source)
        const target = sankeyData.value.nodes.find(node => node.name === params.data.target)
        return [
          `<b>${source?.fullName || params.data.source}</b>`,
          `→ ${target?.fullName || params.data.target}`,
          `value: ${params.data.value || 0}`,
        ].join('<br/>')
      }
      const data = params.data || {}
      return [
        `<b>${data.fullName || data.name}</b>`,
        `类型: ${data.layer || '节点'}`,
        `value: ${params.value || 0}`,
      ].join('<br/>')
    },
  },
  series: [
    {
      type: 'sankey',
      layout: 'none',
      nodeAlign: 'justify',
      draggable: true,
      emphasis: { focus: 'adjacency' },
      data: sankeyData.value.nodes,
      links: sankeyData.value.links,
      label: {
        formatter: (params: any) => params.data?.displayName || params.name,
        fontSize: 12,
        color: '#111827',
      },
      lineStyle: {
        opacity: 0.35,
        curveness: 0.5,
      },
      itemStyle: {
        borderColor: '#ffffff',
        borderWidth: 1,
      },
      top: 40,
      left: 12,
      right: 24,
      bottom: 12,
    },
  ],
}))
</script>

<style scoped>
.sankey-card {
  background: #fff;
  border-radius: 8px;
  padding: 0;
}

.sankey-chart {
  width: 100%;
  height: 320px;
}
</style>
