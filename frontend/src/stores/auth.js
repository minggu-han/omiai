/** 认证状态管理 (Pinia Store) */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('omiai_token') || '')
  const username = ref(localStorage.getItem('omiai_username') || '')

  const isLoggedIn = computed(() => !!token.value)

  async function login(name, password) {
    const data = await api.login(name, password)
    token.value = data.token
    username.value = data.username
    localStorage.setItem('omiai_token', data.token)
    localStorage.setItem('omiai_username', data.username)
  }

  async function register(name, password) {
    const data = await api.register(name, password)
    token.value = data.token
    username.value = data.username
    localStorage.setItem('omiai_token', data.token)
    localStorage.setItem('omiai_username', data.username)
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('omiai_token')
    localStorage.removeItem('omiai_username')
  }

  return { token, username, isLoggedIn, login, register, logout }
})
