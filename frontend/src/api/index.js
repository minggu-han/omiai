/** 后端 API 客户端 */

const BASE = '/api'

/**
 * 创建新的分析会话
 * @returns {Promise<{session_id: string}>}
 */
export async function createSession() {
  const res = await fetch(`${BASE}/session`, { method: 'POST' })
  if (!res.ok) throw new Error(`创建会话失败：${res.statusText}`)
  return res.json()
}

/**
 * 提交聊天记录进行分析（运行 analyzer + generator，在审核节点前中断）
 * @param {Object} params
 * @param {string} params.sessionId
 * @param {Array<{speaker: string, content: string}>} params.chatHistory
 * @param {string|null} params.userPersona
 * @param {string|null} params.userGoal
 * @returns {Promise<{session_id: string, state: Object, is_interrupted: boolean}>}
 */
export async function analyze({ sessionId, chatHistory, userPersona, userGoal }) {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      chat_history: chatHistory,
      user_persona: userPersona || null,
      user_goal: userGoal || null,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `分析失败：${res.statusText}`)
  }
  return res.json()
}

/**
 * 提交人工审核结果，恢复图执行
 * @param {Object} params
 * @param {string} params.sessionId
 * @param {'accept'|'modify'|'reject'} params.decision
 * @param {number} params.selectedIndex
 * @param {string|null} params.modifiedText
 * @returns {Promise<{session_id: string, state: Object, is_interrupted: boolean}>}
 */
export async function review({ sessionId, decision, selectedIndex, modifiedText }) {
  const res = await fetch(`${BASE}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      decision,
      selected_index: selectedIndex,
      modified_text: modifiedText || null,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `提交审核失败：${res.statusText}`)
  }
  return res.json()
}

/**
 * 查询指定会话的当前状态
 * @param {string} sessionId
 * @returns {Promise<{session_id: string, state: Object, is_interrupted: boolean}>}
 */
export async function getState(sessionId) {
  const res = await fetch(`${BASE}/state/${sessionId}`)
  if (!res.ok) throw new Error(`查询状态失败：${res.statusText}`)
  return res.json()
}
