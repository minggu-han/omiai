<!-- AI 约会助攻顾问 —— 主应用组件 -->
<template>
  <div class="app-layout">
    <!-- ============================================================ -->
    <!-- 侧边栏 -->
    <!-- ============================================================ -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>💘 AI 约会助攻顾问</h1>
        <p class="tagline">基于 LangGraph 多智能体协作系统</p>
      </div>

      <!-- API Key -->
      <section class="sidebar-section">
        <h3>⚙️ 配置</h3>
        <label>OpenAI API Key</label>
        <input
          v-model="apiKey"
          type="password"
          placeholder="sk-..."
          @change="onApiKeyChange"
        />
        <span class="help">输入后仅当前会话有效，不会存储</span>
      </section>

      <!-- 用户设定 -->
      <section class="sidebar-section">
        <h3>👤 用户设定</h3>
        <label>你的人设</label>
        <input
          v-model="store.userPersona"
          type="text"
          placeholder="例如：内向理工男、活泼搞笑女..."
        />
        <label>本次聊天目标</label>
        <select v-model="store.userGoal">
          <option value="">-- 不设定 --</option>
          <option>邀约见面</option>
          <option>化解尴尬</option>
          <option>推进关系</option>
          <option>日常聊天</option>
          <option>试探对方</option>
        </select>
      </section>

      <!-- 会话管理 -->
      <section class="sidebar-section">
        <h3>📋 会话管理</h3>
        <div v-if="store.sessionId" class="session-id">
          当前会话: <code>{{ store.sessionId }}</code>
        </div>
        <button class="btn-sidebar" @click="onNewSession" :disabled="store.loading">
          🆕 新建会话
        </button>
        <div class="restore-row">
          <input v-model="restoreId" type="text" placeholder="输入会话 ID..." />
          <button @click="onRestore" :disabled="!restoreId || store.loading">🔄 恢复</button>
        </div>
      </section>
    </aside>

    <!-- ============================================================ -->
    <!-- 主内容区 -->
    <!-- ============================================================ -->
    <main class="main-content">
      <!-- 错误提示 -->
      <div v-if="store.error" class="error-banner">
        {{ store.error }}
        <button @click="store.error = ''">✕</button>
      </div>

      <!-- 加载动画 -->
      <div v-if="store.loading" class="loading">
        <div class="spinner"></div>
        <p>{{ loadingText }}</p>
      </div>

      <!-- 步骤指示器 -->
      <div v-if="store.sessionId" class="steps">
        <span :class="{ active: store.step === 'input' || store.step === 'analyzing' }">1. 输入</span>
        <span class="arrow">→</span>
        <span :class="{ active: store.step === 'review' }">2. 分析</span>
        <span class="arrow">→</span>
        <span :class="{ active: store.step === 'review' && showModifyEditor }">3. 审核</span>
        <span class="arrow">→</span>
        <span :class="{ active: store.step === 'result' }">4. 结果</span>
      </div>

      <!-- 第一步：输入聊天记录 -->
      <ChatInput
        v-if="store.sessionId && (store.step === 'input')"
        :disabled="store.loading"
        @submit="onChatSubmit"
      />

      <!-- 第二步：分析报告 -->
      <AnalysisReport
        v-if="store.analysisReport && (store.step === 'review' || store.step === 'result')"
        :report="store.analysisReport"
      />

      <!-- 第三步：人工审核 -->
      <CandidateReview
        v-if="store.candidates.length > 0 && store.step === 'review'"
        :candidates="store.candidates"
        :retryCount="store.retryCount"
        :showModify="showModifyEditor"
        :modifyIndex="modifyTargetIndex"
        @accept="onAccept"
        @modify="onModifyClick"
        @reject="onReject"
        @cancelModify="showModifyEditor = false"
        @confirmModify="onModifyConfirm"
      />

      <!-- 强制退出（驳回 3 次） -->
      <div v-if="store.step === 'maxRetry'" class="max-retry">
        <h2>🚫 已连续驳回 3 次</h2>
        <p>AI 建议你手动回复。换个角度想想，也许对方并没有那么难回复？</p>
        <button class="btn-primary" @click="onNewSession">开始新会话</button>
      </div>

      <!-- 第四步：最终结果 -->
      <FinalResult
        v-if="store.finalReply && store.step === 'result'"
        :finalReply="store.finalReply"
        :simulation="store.simulation"
      />

      <!-- 底部操作 -->
      <div v-if="store.step === 'result'" class="bottom-actions">
        <button class="btn-primary" @click="onNewSession">🔄 开始新会话</button>
      </div>

      <!-- 空状态引导 -->
      <div v-if="!store.sessionId && !store.loading" class="empty-state">
        <div class="empty-icon">💘</div>
        <h2>欢迎使用 AI 约会助攻顾问</h2>
        <p>在左侧边栏配置 API Key，然后点击「新建会话」开始。</p>
        <p class="empty-sub">分析 → 生成 → 审核 → 润色 → 模拟，五步帮你搞定每次回复。</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useSessionStore } from './stores/session'
import ChatInput from './components/ChatInput.vue'
import AnalysisReport from './components/AnalysisReport.vue'
import CandidateReview from './components/CandidateReview.vue'
import FinalResult from './components/FinalResult.vue'

const store = useSessionStore()

// ---- 本地状态 ----
const apiKey = ref('')
const restoreId = ref('')
const showModifyEditor = ref(false)
const modifyTargetIndex = ref(0)

// ---- 加载文案 ----
const loadingText = computed(() => {
  if (store.step === 'analyzing') return '🤖 AI 正在分析聊天记录...'
  return '🤖 AI 正在处理中...'
})

// ---- 事件处理 ----

function onApiKeyChange() {
  // 将 API Key 传递给后端（通过 header 或 query）
  // 简化方案：后端在每次请求时从环境变量读取
  // 此处仅做前端记录
}

async function onNewSession() {
  showModifyEditor.value = false
  await store.newSession()
}

async function onRestore() {
  await store.restoreSession(restoreId.value)
  restoreId.value = ''
}

async function onChatSubmit(messages) {
  store.chatHistory = messages
  await store.startAnalyze()
}

async function onAccept(index) {
  await store.submitReview('accept', index, null)
}

function onModifyClick(index) {
  modifyTargetIndex.value = index
  showModifyEditor.value = true
}

async function onModifyConfirm(editedText) {
  showModifyEditor.value = false
  await store.submitReview('modify', modifyTargetIndex.value, editedText)
}

async function onReject() {
  await store.submitReview('reject', 0, null)
}
</script>

<style>
/* ============================================================
   全局样式
   ============================================================ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: #f5f5f5; color: #333; line-height: 1.5;
}

/* ============================================================
   布局
   ============================================================ */
.app-layout { display: flex; min-height: 100vh; }

/* ---- 侧边栏 ---- */
.sidebar {
  width: 300px; min-width: 300px; background: #1a1a2e; color: #e0e0e0;
  padding: 24px 20px; display: flex; flex-direction: column; gap: 20px;
  overflow-y: auto;
}
.sidebar-header h1 { font-size: 20px; color: #fff; }
.tagline { font-size: 12px; color: #888; margin-top: 4px; }
.sidebar-section { display: flex; flex-direction: column; gap: 6px; }
.sidebar-section h3 { font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.sidebar-section label { font-size: 13px; color: #ccc; }
.sidebar-section input, .sidebar-section select {
  padding: 8px 12px; border-radius: 8px; border: 1px solid #333;
  background: #16213e; color: #e0e0e0; font-size: 14px;
}
.sidebar-section input:focus, .sidebar-section select:focus {
  outline: none; border-color: #e91e63;
}
.help { font-size: 11px; color: #666; }
.session-id {
  background: #16213e; padding: 8px 12px; border-radius: 8px; font-size: 13px;
}
.session-id code { color: #e91e63; }
.btn-sidebar {
  width: 100%; padding: 10px; border: none; border-radius: 8px;
  background: #e91e63; color: #fff; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
}
.btn-sidebar:hover { background: #c2185b; }
.btn-sidebar:disabled { opacity: 0.5; cursor: not-allowed; }
.restore-row { display: flex; gap: 8px; }
.restore-row input { flex: 1; }
.restore-row button {
  padding: 8px 14px; border: 1px solid #e91e63; border-radius: 8px;
  background: transparent; color: #e91e63; font-size: 13px; cursor: pointer;
}
.restore-row button:hover { background: rgba(233,30,99,0.1); }

/* ---- 主内容区 ---- */
.main-content {
  flex: 1; padding: 40px; max-width: 960px; overflow-y: auto;
}

/* ---- 错误提示 ---- */
.error-banner {
  background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px;
  padding: 12px 16px; margin-bottom: 20px; color: #b91c1c;
  display: flex; justify-content: space-between; align-items: center; font-size: 14px;
}
.error-banner button {
  background: none; border: none; font-size: 18px; color: #b91c1c; cursor: pointer;
}

/* ---- 加载 ---- */
.loading {
  display: flex; flex-direction: column; align-items: center;
  padding: 60px 0; gap: 16px; color: #888;
}
.spinner {
  width: 40px; height: 40px; border: 4px solid #eee;
  border-top-color: #e91e63; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ---- 步骤指示器 ---- */
.steps {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 28px; font-size: 14px; color: #ccc;
}
.steps span { transition: color 0.3s; }
.steps .active { color: #e91e63; font-weight: 600; }
.steps .arrow { color: #ddd; }

/* ---- 空状态 ---- */
.empty-state { text-align: center; padding: 80px 20px; color: #888; }
.empty-icon { font-size: 64px; margin-bottom: 16px; }
.empty-state h2 { color: #333; margin-bottom: 8px; }
.empty-state p { margin-bottom: 4px; }
.empty-sub { font-size: 14px; color: #aaa; margin-top: 12px !important; }

/* ---- 强制退出 ---- */
.max-retry { text-align: center; padding: 60px 0; }
.max-retry h2 { color: #ef4444; margin-bottom: 12px; }
.max-retry p { color: #666; margin-bottom: 24px; }

/* ---- 全局按钮 ---- */
.btn-primary {
  padding: 12px 32px; border: none; border-radius: 10px;
  background: #e91e63; color: #fff; font-size: 16px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
}
.btn-primary:hover { background: #c2185b; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

/* ---- 底部操作 ---- */
.bottom-actions { text-align: center; margin-top: 32px; }
</style>
