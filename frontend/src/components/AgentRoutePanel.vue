<template>
  <a-card class="soft-card" :bordered="false">
    <template #title>Agent 路由信息</template>
    <a-empty v-if="!routeInfo" description="暂无路由信息" />
    <div v-else class="route-list">
      <div class="route-item">
        <span>intent</span>
        <a-tag color="blue">{{ routeInfo.intent }}</a-tag>
      </div>
      <div class="route-item">
        <span>need_pdf_search</span>
        <a-tag :color="routeInfo.need_pdf_search ? 'green' : 'orange'">{{ routeInfo.need_pdf_search }}</a-tag>
      </div>
      <div class="route-block">
        <b>search_keywords</b>
        <div class="tags">
          <a-tag v-for="keyword in routeInfo.search_keywords || []" :key="keyword" color="cyan">
            {{ keyword }}
          </a-tag>
        </div>
      </div>
      <div class="route-block">
        <b>expanded_query</b>
        <p>{{ routeInfo.expanded_query || '-' }}</p>
      </div>
      <div class="route-block">
        <b>answer_focus</b>
        <p>{{ routeInfo.answer_focus || '-' }}</p>
      </div>
      <div class="route-block">
        <b>user_emotion_reply</b>
        <p>{{ routeInfo.user_emotion_reply || '-' }}</p>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { RouteInfo } from '../types/api'

defineProps<{
  routeInfo: RouteInfo | null
}>()
</script>

<style scoped>
.route-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.route-item {
  display: flex;
  justify-content: space-between;
  color: #475569;
}

.route-block b {
  display: block;
  margin-bottom: 6px;
  color: #102033;
}

.route-block p {
  margin: 0;
  color: #475569;
  line-height: 1.55;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
