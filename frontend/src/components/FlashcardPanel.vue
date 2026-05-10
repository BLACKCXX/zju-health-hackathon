<template>
  <a-card class="soft-card" :bordered="false">
    <template #title>知识闪卡</template>
    <a-empty v-if="flashcards.length === 0" description="暂无闪卡" />
    <a-space v-else direction="vertical" class="cards">
      <a-card v-for="card in flashcards" :key="card.title" size="small" class="flashcard">
        <h3>{{ card.title }}</h3>
        <p>{{ card.definition }}</p>
        <ul>
          <li v-for="point in card.key_points" :key="point">{{ point }}</li>
        </ul>
        <a-space wrap>
          <a-tag v-for="term in card.related_terms" :key="term" color="cyan">{{ term }}</a-tag>
        </a-space>
        <a-button class="graph-btn" type="primary" block @click="$emit('build-graph', card.title)">
          生成图谱
        </a-button>
      </a-card>
    </a-space>
  </a-card>
</template>

<script setup lang="ts">
import type { Flashcard } from '../types/api'
defineProps<{ flashcards: Flashcard[] }>()
defineEmits<{ 'build-graph': [topic: string] }>()
</script>

<style scoped>
.cards {
  width: 100%;
}
.flashcard {
  border-radius: 12px;
}
.flashcard h3 {
  margin: 0 0 8px;
}
.graph-btn {
  margin-top: 12px;
}
</style>
