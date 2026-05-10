<template>
  <a-card class="soft-card" :bordered="false">
    <template #title>ECharts 检索可视化</template>
    <a-empty v-if="chunks.length === 0" description="暂无数据" />
    <div v-else class="charts">
      <VChart class="chart" :option="barOption" autoresize />
      <VChart class="chart" :option="pieOption" autoresize />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import type { RetrievedChunk } from '../types/api'

use([CanvasRenderer, BarChart, PieChart, GridComponent, LegendComponent, TooltipComponent])

const props = defineProps<{
  chunks: RetrievedChunk[]
}>()

const barOption = computed(() => ({
  tooltip: {},
  grid: { left: 42, right: 16, top: 28, bottom: 42 },
  xAxis: {
    type: 'category',
    data: props.chunks.map((item, index) => `${index + 1}@${item.page}`),
  },
  yAxis: { type: 'value' },
  series: [
    {
      name: 'score',
      type: 'bar',
      data: props.chunks.map((item) => Number((item.score || 0).toFixed(4))),
      itemStyle: { color: '#0f766e' },
    },
  ],
}))

const pieOption = computed(() => {
  const countMap = new Map<string, number>()
  props.chunks.forEach((item) => countMap.set(item.source_file, (countMap.get(item.source_file) || 0) + 1))
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll' },
    series: [
      {
        name: '来源教材',
        type: 'pie',
        radius: ['36%', '66%'],
        data: Array.from(countMap.entries()).map(([name, value]) => ({ name, value })),
      },
    ],
  }
})
</script>

<style scoped>
.charts {
  display: grid;
  gap: 14px;
}

.chart {
  width: 100%;
  height: 240px;
}
</style>
