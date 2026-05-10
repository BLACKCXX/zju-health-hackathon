<template>
  <a-segmented
    :value="mode"
    :options="options"
    @change="handleChange"
  />
</template>

<script setup lang="ts">
defineProps<{ mode: 'ask' | 'graph' | 'textbook' }>()
const emit = defineEmits<{ 'update:mode': [mode: 'ask' | 'graph' | 'textbook'] }>()

const options = [
  { label: '教材管理', value: 'textbook' },
  { label: '知识小回答', value: 'ask' },
  { label: '知识图谱工作台', value: 'graph' },
]

function handleChange(value: string | number) {
  const val = value as string
  if (val === 'graph') emit('update:mode', 'graph')
  else if (val === 'textbook') emit('update:mode', 'textbook')
  else emit('update:mode', 'ask')
}
</script>