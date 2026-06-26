<!-- 第一步：聊天记录输入组件 -->
<template>
  <div class="chat-input">
    <h2>📝 第一步：输入聊天记录</h2>
    <p class="hint">格式要求：每行一条消息，以「对方：」或「我：」开头</p>

    <textarea
      v-model="text"
      placeholder="对方：今天好累啊&#10;我：怎么了？工作太忙了吗&#10;对方：是啊，老板又加需求&#10;我：哈哈，IT行业的日常&#10;对方：你倒是挺理解的嘛"
      rows="8"
      :disabled="disabled"
    ></textarea>

    <button
      class="btn-primary"
      :disabled="disabled || !text.trim()"
      @click="$emit('submit', parsedMessages)"
    >
      🚀 开始分析
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  initialText: { type: String, default: '' },
})

defineEmits(['submit'])

const text = ref(props.initialText || '')

// 当 initialText 变化时（如恢复会话），同步到 textarea
watch(() => props.initialText, (val) => {
  if (val) text.value = val
})

/** 将文本解析为聊天消息数组 */
const parsedMessages = computed(() => {
  const messages = []
  if (!text.value.trim()) return messages

  for (const line of text.value.trim().split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (trimmed.startsWith('对方：')) {
      messages.push({ speaker: 'other', content: trimmed.slice(3) })
    } else if (trimmed.startsWith('我：')) {
      messages.push({ speaker: 'me', content: trimmed.slice(2) })
    } else if (trimmed.includes('：')) {
      const idx = trimmed.indexOf('：')
      messages.push({ speaker: 'other', content: trimmed.slice(idx + 1).trim() })
    }
  }
  return messages
})
</script>

<style scoped>
.chat-input { max-width: 640px; }
.hint { color: #888; font-size: 14px; margin-bottom: 12px; }
textarea {
  width: 100%; padding: 14px; border-radius: 10px;
  border: 1px solid #ddd; font-size: 15px; line-height: 1.6;
  resize: vertical; font-family: inherit;
}
textarea:focus { outline: none; border-color: #e91e63; box-shadow: 0 0 0 3px rgba(233,30,99,0.1); }
</style>
