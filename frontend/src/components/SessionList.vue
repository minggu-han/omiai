<!-- 存档列表组件 —— 显示用户所有历史会话 -->
<template>
  <div class="session-list">
    <div v-if="loading" class="sl-loading">加载中...</div>
    <div v-else-if="error" class="sl-error">{{ error }}</div>
    <div v-else-if="sessions.length === 0" class="sl-empty">暂无存档</div>
    <div
      v-for="s in sessions"
      :key="s.session_id"
      class="sl-item"
      @click="$emit('restore', s.session_id)"
    >
      <div class="sl-title">{{ s.title }}</div>
      <div class="sl-meta">
        <span class="sl-step">{{ stepLabel(s.current_step) }}</span>
        <span class="sl-time">{{ fmtTime(s.updated_at) }}</span>
      </div>
      <button class="sl-delete" @click.stop="$emit('delete', s.session_id)" title="删除">✕</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from '../api'

defineEmits(['restore', 'delete'])

const sessions = ref([])
const loading = ref(false)
const error = ref('')

const stepLabel = (s) => ({
  input: '📝 未开始',
  review: '⏸️ 待审核',
  result: '✅ 已完成',
  maxRetry: '🚫 已超限',
}[s] || s)

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.fetchSessions()
    sessions.value = data.sessions || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

// 暴露 refresh 给父组件调用
defineExpose({ refresh: load })
</script>

<style scoped>
.session-list { display: flex; flex-direction: column; gap: 6px; }
.sl-loading, .sl-error, .sl-empty { font-size: 12px; color: #888; padding: 8px 0; }
.sl-error { color: #f87171; }
.sl-item {
  position: relative; background: #16213e; border-radius: 8px;
  padding: 10px 12px; cursor: pointer; transition: background 0.2s;
}
.sl-item:hover { background: #1f3060; }
.sl-title { font-size: 13px; color: #e0e0e0; margin-bottom: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 20px; }
.sl-meta { display: flex; justify-content: space-between; font-size: 11px; color: #888; }
.sl-delete {
  position: absolute; top: 8px; right: 8px; background: none; border: none;
  color: #666; font-size: 14px; cursor: pointer; padding: 2px 6px; border-radius: 4px;
}
.sl-delete:hover { color: #ef4444; background: rgba(239,68,68,0.1); }
</style>
