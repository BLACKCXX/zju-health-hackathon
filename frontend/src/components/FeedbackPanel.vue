<template>
  <a-card class="soft-card" :bordered="false">
    <template #title>教师反馈</template>
    <a-empty v-if="!targetId" description="请先点击图谱中的节点" />
    <template v-else>
      <a-textarea v-model:value="comment" placeholder="添加教师备注，说明修改原因" :rows="3" />
      <a-space wrap class="actions">
        <a-button @click="submit('keep')">保留</a-button>
        <a-button danger @click="submit('delete')">删除</a-button>
        <a-button @click="submit('split')">拆分</a-button>
        <a-button @click="submit('merge')">合并</a-button>
        <a-button type="primary" @click="submit('edit')">修改说明</a-button>
      </a-space>
    </template>
  </a-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  targetId: string | null
  targetType?: 'node' | 'edge' | null
}>()

const emit = defineEmits<{
  feedback: [action: 'keep' | 'delete' | 'split' | 'merge' | 'edit', comment: string]
}>()

const comment = ref('')

function submit(action: 'keep' | 'delete' | 'split' | 'merge' | 'edit') {
  if (!props.targetId) return
  emit('feedback', action, comment.value)
  comment.value = ''
}
</script>

<style scoped>
.actions {
  margin-top: 12px;
}
</style>