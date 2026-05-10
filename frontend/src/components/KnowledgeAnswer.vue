<template>
  <a-card class="soft-card answer-card" :bordered="false">
    <template #title>知识小回答</template>
    <a-empty v-if="!answer" description="请输入问题开始检索教材证据" />
    <div v-else>
      <div class="markdown-text">{{ answer.answer }}</div>
      <a-divider />
      <h4>引用来源</h4>
      <a-list :data-source="answer.citations" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-tag color="blue">{{ item.book }}</a-tag>
            <span>{{ item.chapter }} · 第 {{ item.page }} 页：{{ item.quote }}</span>
          </a-list-item>
        </template>
      </a-list>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { AskResponse } from '../types/api'
defineProps<{ answer: AskResponse | null }>()
</script>

<style scoped>
.answer-card {
  min-height: 360px;
}
h4 {
  margin: 0 0 10px;
}
</style>
