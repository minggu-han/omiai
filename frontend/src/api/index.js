/** 后端 API 客户端 */

const BASE = '/api'

// ---------------------------------------------------------------------------
// 内部辅助
// ---------------------------------------------------------------------------

function getToken() {
  return localStorage.getItem('omiai_token') || ''
}

async function request(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  if (getToken()) {
    headers['Authorization'] = `Bearer ${getToken()}`
  }

  const res = await fetch(`${BASE}${url}`, { ...options, headers })

  if (!res.ok) {
    // 401 且已有 token → token 过期，自动登出
    if (res.status === 401 && getToken()) {
      localStorage.removeItem('omiai_token')
      localStorage.removeItem('omiai_username')
      window.location.reload()
      throw new Error('登录已过期，请重新登录')
    }
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `请求失败：${res.statusText}`)
  }

  return res.json()
}

// ---------------------------------------------------------------------------
// 认证
// ---------------------------------------------------------------------------

export async function login(username, password) {
  return request('/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function register(username, password) {
  return request('/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

// ---------------------------------------------------------------------------
// 会话管理
// ---------------------------------------------------------------------------

export async function fetchSessions() {
  return request('/sessions')
}

export async function deleteSession(sessionId) {
  return request(`/sessions/${sessionId}`, { method: 'DELETE' })
}

// ---------------------------------------------------------------------------
// 工作流
// ---------------------------------------------------------------------------

/**
 * 创建新的分析会话
 */
export async function createSession() {
  return request('/session', { method: 'POST' })
}

/**
 * 提交聊天记录进行分析
 */
export async function analyze({ sessionId, chatHistory, userPersona, userGoal }) {
  return request('/analyze', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      chat_history: chatHistory,
      user_persona: userPersona || null,
      user_goal: userGoal || null,
    }),
  })
}

/**
 * 提交人工审核结果，恢复图执行
 */
export async function review({ sessionId, decision, selectedIndex, modifiedText }) {
  return request('/review', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      decision,
      selected_index: selectedIndex,
      modified_text: modifiedText || null,
    }),
  })
}

/**
 * 查询指定会话的当前状态
 */
export async function getState(sessionId) {
  return request(`/state/${sessionId}`)
}
