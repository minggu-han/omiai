<!-- 第三步：人工审核组件 —— 展示 3 条候选回复并接受用户操作 -->
<template>
  <div class="candidate-review">
    <h2>⚠️ 第三步：人工审核</h2>
    <p class="subtitle">请审核以下 3 条 AI 生成的候选回复，选择你的操作。</p>

    <!-- 重试提示 -->
    <div v-if="retryCount > 0" class="retry-warning">
      ⏳ 第 {{ retryCount }} 次重新生成（最多 3 次）
    </div>

    <!-- 3 条候选回复卡片 -->
    <div class="cards-row">
      <div
        v-for="(cand, i) in candidates"
        :key="i"
        class="candidate-card"
        :class="{ selected: selectedIndex === i && showModify }"
      >
        <div class="card-header">
          <span class="style-badge" :class="'style-' + cand.style">{{ styleEmoji[cand.style] || '💬' }} {{ cand.style }}风</span>
        </div>

        <div class="reply-preview">
          <blockquote>{{ cand.reply }}</blockquote>
        </div>

        <div class="strategy">
          <strong>策略说明：</strong>{{ cand.strategy_explain }}
        </div>

        <div class="card-actions">
          <button class="btn-accept" @click="$emit('accept', i)">✅ 选这条</button>
          <button class="btn-modify" @click="$emit('modify', i)">✏️ 修改</button>
        </div>
      </div>
    </div>

    <!-- 全局驳回按钮 -->
    <button class="btn-reject" @click="$emit('reject')">🔄 全部驳回，重新生成</button>

    <!-- 修改编辑器（弹出） -->
    <div v-if="showModify" class="modify-overlay" @click.self="$emit('cancelModify')">
      <div class="modify-panel">
        <h3>✏️ 修改回复</h3>
        <textarea
          v-model="editedText"
          rows="4"
          placeholder="编辑回复内容..."
        ></textarea>
        <div class="modify-actions">
          <button class="btn-cancel" @click="$emit('cancelModify')">取消</button>
          <button class="btn-confirm" @click="$emit('confirmModify', editedText)">✅ 确认修改并提交</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  candidates: { type: Array, required: true },
  retryCount: { type: Number, default: 0 },
  showModify: { type: Boolean, default: false },
  modifyIndex: { type: Number, default: 0 },
})

defineEmits(['accept', 'modify', 'reject', 'cancelModify', 'confirmModify'])

const selectedIndex = ref(0)
const editedText = ref('')

// 当父组件切换修改模式时，自动填充原始文本
watch(() => props.showModify, (val) => {
  if (val && props.candidates[props.modifyIndex]) {
    selectedIndex.value = props.modifyIndex
    editedText.value = props.candidates[props.modifyIndex].reply || ''
  }
})

const styleEmoji = { '幽默': '😄', '温暖': '🤗', '推拉': '😏' }
</script>

<style scoped>
.candidate-review { margin-top: 24px; }
.subtitle { color: #888; font-size: 14px; margin-bottom: 16px; }
.retry-warning {
  background: #fff3cd; color: #856404; padding: 10px 16px;
  border-radius: 8px; margin-bottom: 16px; font-size: 14px;
}
.cards-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
.candidate-card {
  background: #fff; border-radius: 12px; padding: 20px;
  border: 2px solid #eee; display: flex; flex-direction: column;
  transition: border-color 0.2s;
}
.candidate-card.selected { border-color: #e91e63; }
.card-header { margin-bottom: 12px; }
.style-badge {
  display: inline-block; padding: 4px 12px; border-radius: 20px;
  font-size: 13px; font-weight: 600;
}
.style-幽默 { background: #fef3c7; color: #92400e; }
.style-温暖 { background: #dbeafe; color: #1e40af; }
.style-推拉 { background: #fce7f3; color: #9d174d; }
.reply-preview { flex: 1; margin-bottom: 12px; }
blockquote {
  background: #f9fafb; border-left: 3px solid #e91e63; padding: 10px 14px;
  margin: 0; border-radius: 0 8px 8px 0; font-size: 15px; line-height: 1.5; color: #333;
}
.strategy { font-size: 12px; color: #888; margin-bottom: 16px; line-height: 1.5; }
.card-actions { display: flex; gap: 8px; }
.btn-accept, .btn-modify {
  flex: 1; padding: 8px 0; border: none; border-radius: 8px;
  font-size: 14px; cursor: pointer; transition: all 0.2s;
}
.btn-accept { background: #e91e63; color: #fff; }
.btn-accept:hover { background: #c2185b; }
.btn-modify { background: #f3f4f6; color: #374151; }
.btn-modify:hover { background: #e5e7eb; }
.btn-reject {
  width: 100%; padding: 12px; border: 2px dashed #d1d5db; border-radius: 10px;
  background: transparent; color: #6b7280; font-size: 15px; cursor: pointer;
  transition: all 0.2s;
}
.btn-reject:hover { border-color: #ef4444; color: #ef4444; }

/* 修改编辑器浮层 */
.modify-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modify-panel {
  background: #fff; border-radius: 16px; padding: 28px; width: 480px; max-width: 90vw;
}
.modify-panel h3 { margin-bottom: 16px; }
.modify-panel textarea {
  width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #ddd;
  font-size: 15px; line-height: 1.6; resize: vertical; font-family: inherit;
}
.modify-panel textarea:focus { outline: none; border-color: #e91e63; }
.modify-actions { display: flex; gap: 12px; margin-top: 16px; justify-content: flex-end; }
.btn-cancel {
  padding: 10px 20px; border: 1px solid #ddd; border-radius: 8px;
  background: #fff; cursor: pointer;
}
.btn-confirm {
  padding: 10px 20px; border: none; border-radius: 8px;
  background: #e91e63; color: #fff; font-weight: 600; cursor: pointer;
}
</style>
