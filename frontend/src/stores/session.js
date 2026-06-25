/** 会话状态管理 (Pinia Store) */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api'

export const useSessionStore = defineStore('session', () => {
  // ---- 基础状态 ----
  const sessionId = ref('')
  const loading = ref(false)
  const error = ref('')

  // ---- 工作流状态 ----
  const step = ref('input') // 'input' | 'analyzing' | 'review' | 'result' | 'maxRetry'
  const chatHistory = ref([])
  const userPersona = ref('')
  const userGoal = ref('')

  // 从后端同步回来的状态
  const analysisReport = ref(null)
  const candidates = ref([])
  const finalReply = ref('')
  const simulation = ref(null)
  const retryCount = ref(0)

  // ---- 计算属性 ----
  const isInterrupted = computed(() => step.value === 'review')

  // ---- 操作 ----

  /** 新建会话 */
  async function newSession() {
    loading.value = true
    error.value = ''
    try {
      const data = await api.createSession()
      sessionId.value = data.session_id
      resetState()
      step.value = 'input'
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /** 提交聊天记录开始分析 */
  async function startAnalyze() {
    if (!sessionId.value) {
      error.value = '请先创建会话'
      return
    }
    if (chatHistory.value.length === 0) {
      error.value = '请输入聊天记录'
      return
    }

    loading.value = true
    error.value = ''
    step.value = 'analyzing'

    try {
      const data = await api.analyze({
        sessionId: sessionId.value,
        chatHistory: chatHistory.value,
        userPersona: userPersona.value,
        userGoal: userGoal.value,
      })
      applyState(data.state)
      if (data.is_interrupted) {
        step.value = 'review'
      } else {
        step.value = 'result'
      }
    } catch (e) {
      error.value = e.message
      step.value = 'input'
    } finally {
      loading.value = false
    }
  }

  /** 提交审核决策 */
  async function submitReview(decision, selectedIndex, modifiedText) {
    loading.value = true
    error.value = ''

    try {
      const data = await api.review({
        sessionId: sessionId.value,
        decision,
        selectedIndex,
        modifiedText,
      })
      applyState(data.state)

      if (data.is_interrupted) {
        // 驳回后再次中断 → 新一轮审核
        step.value = 'review'
      } else if (data.state.retry_count >= 3 && !data.state.final_reply) {
        // 达到最大重试次数，强制退出
        step.value = 'maxRetry'
      } else {
        step.value = 'result'
      }
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /** 恢复已有会话 */
  async function restoreSession(id) {
    loading.value = true
    error.value = ''
    try {
      const data = await api.getState(id)
      sessionId.value = id
      applyState(data.state)

      if (data.is_interrupted) {
        step.value = 'review'
      } else if (data.state.analysis_report || data.state.final_reply) {
        step.value = data.state.final_reply ? 'result' : 'review'
      } else {
        step.value = 'input'
      }
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  // ---- 内部辅助 ----

  function applyState(state) {
    if (state.analysis_report) analysisReport.value = state.analysis_report
    if (state.candidates) candidates.value = state.candidates
    if (state.final_reply) finalReply.value = state.final_reply
    if (state.simulation) simulation.value = state.simulation
    if (state.retry_count !== undefined) retryCount.value = state.retry_count
  }

  function resetState() {
    chatHistory.value = []
    analysisReport.value = null
    candidates.value = []
    finalReply.value = ''
    simulation.value = null
    retryCount.value = 0
    error.value = ''
  }

  return {
    sessionId, loading, error, step,
    chatHistory, userPersona, userGoal,
    analysisReport, candidates, finalReply, simulation, retryCount,
    isInterrupted,
    newSession, startAnalyze, submitReview, restoreSession,
  }
})
