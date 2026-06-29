<!-- AI 聊天顾问系统 —— 主应用组件 -->
<template>
  <!-- ============================================================ -->
  <!-- 未登录 → 登录/注册页 -->
  <!-- ============================================================ -->
  <LoginForm v-if="!auth.isLoggedIn" @loggedIn="onLoggedIn" />

  <!-- ============================================================ -->
  <!-- 已登录 → 主界面 -->
  <!-- ============================================================ -->
  <div v-else class="app-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>💬 AI 聊天顾问系统</h1>
        <p class="tagline">基于 LangGraph 多智能体协作系统</p>
      </div>

      <!-- 用户信息 -->
      <section class="sidebar-section">
        <h3>👤 当前用户</h3>
        <div class="user-row">
          <span>{{ auth.username }}</span>
          <button class="btn-logout" @click="onLogout">退出</button>
        </div>
      </section>

      <!-- 用户设定 -->
      <section class="sidebar-section">
        <h3>⚙️ 用户设定</h3>
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
      </section>

      <!-- 历史存档 -->
      <section class="sidebar-section">
        <h3>💾 历史存档</h3>
        <SessionList
          ref="sessionListRef"
          @restore="onRestore"
          @delete="onDeleteSession"
        />
      </section>
    </aside>

    <!-- 主内容区 -->
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
        :initialText="chatHistoryText"
        @submit="onChatSubmit"
      />

      <!-- 聊天记录回顾（非 input 步骤时显示只读历史） -->
      <div v-if="store.sessionId && store.step !== 'input' && store.chatHistory.length > 0" class="history-section">
        <h3>💬 聊天记录</h3>
        <div class="history-messages">
          <div
            v-for="(m, i) in store.chatHistory"
            :key="i"
            class="history-msg"
            :class="'msg-' + m.speaker"
          >
            <span class="msg-speaker">{{ m.speaker === 'me' ? '我' : '对方' }}</span>
            <span class="msg-content">{{ m.content }}</span>
          </div>
        </div>
      </div>

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
        <div class="empty-icon">💬</div>
        <h2>欢迎回来，{{ auth.username }}</h2>
        <p>点击「新建会话」开始分析，或从左侧存档中恢复之前的会话。</p>
        <p class="empty-sub">分析 → 生成 → 审核 → 润色 → 模拟，五步完成每次回复。</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useSessionStore } from './stores/session'
import { useAuthStore } from './stores/auth'
import ChatInput from './components/ChatInput.vue'
import AnalysisReport from './components/AnalysisReport.vue'
import CandidateReview from './components/CandidateReview.vue'
import FinalResult from './components/FinalResult.vue'
import LoginForm from './components/LoginForm.vue'
import SessionList from './components/SessionList.vue'

const store = useSessionStore()
const auth = useAuthStore()

// ---- 本地状态 ----
const showModifyEditor = ref(false)
const modifyTargetIndex = ref(0)
const sessionListRef = ref(null)

// ---- 派生数据 ----

/** 将 chatHistory 数组还原为文本（中文格式：对方：xxx / 我：xxx） */
const chatHistoryText = computed(() => {
  if (!store.chatHistory || store.chatHistory.length === 0) return ''
  return store.chatHistory.map(m => {
    const label = m.speaker === 'me' ? '我' : '对方'
    return `${label}：${m.content}`
  }).join('\n')
})

// ---- 加载文案 ----
const loadingText = computed(() => {
  if (store.step === 'analyzing') return '🤖 AI 正在分析聊天记录...'
  return '🤖 AI 正在处理中...'
})

// ---- 事件处理 ----

function onLoggedIn() {
  // 登录成功后刷新存档列表
  sessionListRef.value?.refresh()
}

function onLogout() {
  auth.logout()
  store.resetState?.()
}

async function onNewSession() {
  showModifyEditor.value = false
  await store.newSession()
  // 刷新存档列表
  sessionListRef.value?.refresh()
}

async function onRestore(sessionId) {
  showModifyEditor.value = false
  await store.restoreSession(sessionId)
}

async function onDeleteSession(sessionId) {
  await store.removeSession(sessionId)
  sessionListRef.value?.refresh()
}

async function onChatSubmit(messages) {
  store.chatHistory = messages
  await store.startAnalyze()
  // 分析完成后刷新存档列表（标题会更新）
  sessionListRef.value?.refresh()
}

async function onAccept(index) {
  await store.submitReview('accept', index, null)
  sessionListRef.value?.refresh()
}

function onModifyClick(index) {
  modifyTargetIndex.value = index
  showModifyEditor.value = true
}

async function onModifyConfirm(editedText) {
  showModifyEditor.value = false
  await store.submitReview('modify', modifyTargetIndex.value, editedText)
  sessionListRef.value?.refresh()
}

async function onReject() {
  await store.submitReview('reject', 0, null)
  sessionListRef.value?.refresh()
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
.user-row {
  display: flex; justify-content: space-between; align-items: center;
  background: #16213e; padding: 8px 12px; border-radius: 8px; font-size: 14px;
}
.btn-logout {
  background: transparent; border: 1px solid #888; color: #888;
  padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;
}
.btn-logout:hover { border-color: #e91e63; color: #e91e63; }
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

/* ---- 聊天记录回顾 ---- */
.history-section {
  margin-bottom: 24px; padding: 16px 20px;
  background: #fff; border-radius: 12px; border: 1px solid #e5e7eb;
}
.history-section h3 { margin-bottom: 12px; font-size: 15px; color: #555; }
.history-messages { display: flex; flex-direction: column; gap: 6px; }
.history-msg { padding: 6px 10px; border-radius: 6px; font-size: 14px; }
.msg-me { background: #fce7f3; text-align: right; }
.msg-other { background: #f3f4f6; }
.msg-speaker { font-weight: 600; font-size: 12px; color: #888; margin-right: 6px; }
.msg-me .msg-speaker { margin-right: 0; margin-left: 6px; order: 2; }

/* ---- 底部操作 ---- */
.bottom-actions { text-align: center; margin-top: 32px; }
</style>
