<!-- 登录 / 注册页面 -->
<template>
  <div class="login-overlay">
    <div class="login-card">
      <div class="login-header">
        <h1>💬 AI 聊天顾问系统</h1>
        <p>登录后才能使用系统</p>
      </div>

      <!-- Tab 切换 -->
      <div class="tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>

      <form @submit.prevent="onSubmit">
        <label>用户名</label>
        <input v-model="form.username" type="text" placeholder="输入用户名" required autocomplete="username" />

        <label>密码</label>
        <input v-model="form.password" type="password" placeholder="输入密码" required autocomplete="current-password" />

        <div v-if="errorMsg" class="login-error">{{ errorMsg }}</div>

        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['loggedIn'])
const auth = useAuthStore()

const mode = ref('login')
const loading = ref(false)
const errorMsg = ref('')
const form = ref({ username: '', password: '' })

async function onSubmit() {
  loading.value = true
  errorMsg.value = ''
  try {
    if (mode.value === 'login') {
      await auth.login(form.value.username, form.value.password)
    } else {
      await auth.register(form.value.username, form.value.password)
    }
    emit('loggedIn')
  } catch (e) {
    errorMsg.value = e.message || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-overlay {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
.login-card {
  background: #fff; border-radius: 16px; padding: 40px;
  width: 400px; max-width: 90vw; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.login-header { text-align: center; margin-bottom: 24px; }
.login-header h1 { font-size: 24px; color: #1a1a2e; margin-bottom: 4px; }
.login-header p { color: #888; font-size: 14px; }
.tabs { display: flex; gap: 0; margin-bottom: 24px; border-radius: 10px; overflow: hidden; border: 1px solid #e5e7eb; }
.tabs button {
  flex: 1; padding: 10px; border: none; background: #f9fafb;
  font-size: 14px; cursor: pointer; transition: all 0.2s;
}
.tabs button.active { background: #e91e63; color: #fff; font-weight: 600; }
label { display: block; font-size: 13px; color: #555; margin-bottom: 4px; margin-top: 12px; }
input {
  width: 100%; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px;
  font-size: 14px; box-sizing: border-box;
}
input:focus { outline: none; border-color: #e91e63; }
.login-error {
  margin-top: 12px; padding: 8px 12px; background: #fef2f2;
  border: 1px solid #fecaca; border-radius: 8px; color: #b91c1c; font-size: 13px;
}
.btn-submit {
  width: 100%; margin-top: 20px; padding: 12px; border: none; border-radius: 10px;
  background: #e91e63; color: #fff; font-size: 16px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
}
.btn-submit:hover { background: #c2185b; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
