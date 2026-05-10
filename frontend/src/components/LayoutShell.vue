<template>
  <main class="app-shell">
    <header class="hero soft-card">
      <div>
        <h1>学科知识整合智能体 / HealthPDF Agent</h1>
        <p>面向医学教材的 RAG + 知识图谱工作台</p>
      </div>
      <ModeSwitcher :mode="mode" @update:mode="$emit('update:mode', $event)" />
    </header>
    <slot />
  </main>
</template>

<script setup lang="ts">
import ModeSwitcher from './ModeSwitcher.vue'
defineProps<{ mode: 'ask' | 'graph' | 'textbook' }>()
defineEmits<{ 'update:mode': [mode: 'ask' | 'graph' | 'textbook'] }>()
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
  gap: 18px;
  margin-bottom: 18px;
  padding: 22px 26px;
  background: linear-gradient(135deg, #ffffff 0%, #eef7f4 55%, #edf4ff 100%);
}
h1 {
  margin: 0;
  color: #102033;
  font-size: 28px;
}
p {
  margin: 8px 0 0;
  color: #0f766e;
  font-weight: 700;
}
</style>