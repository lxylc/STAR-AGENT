<template>
  <div class="auth-page">
    <div class="auth-card" :class="{ 'auth-card--signup': isSignUp }">
      <!-- 登录表单 -->
      <div class="auth-panel auth-panel--form auth-panel--signin">
        <form class="auth-form" @submit.prevent="onLogin">
          <h2 class="auth-title">登录</h2>
          <input
            v-model="loginForm.username"
            class="auth-input"
            type="text"
            placeholder="用户名"
            autocomplete="username"
            required
          />
          <input
            v-model="loginForm.password"
            class="auth-input"
            type="password"
            placeholder="密码"
            autocomplete="current-password"
            required
          />
          <div class="auth-role">
            <label class="auth-role__item">
              <input v-model="loginForm.role" type="radio" value="student" />
              <span>学生</span>
            </label>
            <label class="auth-role__item">
              <input v-model="loginForm.role" type="radio" value="admin" />
              <span>管理员</span>
            </label>
          </div>
          <button class="auth-btn" type="submit" :disabled="loginLoading">
            {{ loginLoading ? '登录中…' : '登录' }}
          </button>
        </form>
      </div>

      <!-- 注册表单 -->
      <div class="auth-panel auth-panel--form auth-panel--signup">
        <form class="auth-form" @submit.prevent="onRegister">
          <h2 class="auth-title">注册</h2>
          <input
            v-model="registerForm.username"
            class="auth-input"
            type="text"
            placeholder="用户名"
            autocomplete="username"
            required
          />
          <input
            v-model="registerForm.password"
            class="auth-input"
            type="password"
            placeholder="密码"
            autocomplete="new-password"
            required
          />
          <input
            v-model="registerForm.realName"
            class="auth-input"
            type="text"
            placeholder="姓名（可选）"
          />
          <button class="auth-btn" type="submit" :disabled="registerLoading">
            {{ registerLoading ? '注册中…' : '注册' }}
          </button>
        </form>
      </div>

      <!-- 滑动遮罩层 -->
      <div class="auth-overlay">
        <div class="auth-overlay__inner">
          <div class="auth-overlay__panel auth-overlay__panel--left">
            <h2 class="auth-overlay__title">欢迎回来</h2>
            <p class="auth-overlay__text">已有账号？点击下方按钮登录</p>
            <button class="auth-btn auth-btn--ghost" type="button" @click="switchToSignIn">
              登录
            </button>
          </div>
          <div class="auth-overlay__panel auth-overlay__panel--right">
            <h2 class="auth-overlay__title">加入我们</h2>
            <p class="auth-overlay__text">还没有账号？立即注册开始学习</p>
            <button class="auth-btn auth-btn--ghost" type="button" @click="switchToSignUp">
              注册
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register, saveAuth, getStudentId } from '../api/auth'
import { trackBehavior } from '../api/behavior'

const route = useRoute()
const router = useRouter()

const isSignUp = ref(route.path === '/register')
const loginLoading = ref(false)
const registerLoading = ref(false)

const loginForm = reactive({ username: '', password: '', role: 'student' })
const registerForm = reactive({ username: '', password: '', realName: '' })

watch(
  () => route.path,
  (path) => {
    isSignUp.value = path === '/register'
  }
)

function switchToSignIn() {
  isSignUp.value = false
  if (route.path !== '/login') router.replace('/login')
}

function switchToSignUp() {
  isSignUp.value = true
  if (route.path !== '/register') router.replace('/register')
}

async function onLogin() {
  loginLoading.value = true
  try {
    const auth = await login(loginForm)
    saveAuth(auth)
    const sid = auth.studentId || getStudentId()
    if (sid) trackBehavior(sid, 'login', { username: auth.username })
    ElMessage.success('登录成功')
    router.push(auth.role === 'admin' ? '/admin/students' : '/chat')
  } finally {
    loginLoading.value = false
  }
}

async function onRegister() {
  registerLoading.value = true
  try {
    const auth = await register(registerForm)
    saveAuth(auth)
    ElMessage.success('注册成功')
    router.push('/chat')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
  background: #8a9eb0;
  overflow: hidden;
}

.auth-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('/images/auth-bg.png') center 42% / cover no-repeat;
  filter: saturate(0.55) brightness(0.96);
  z-index: 0;
}

.auth-page > * {
  position: relative;
  z-index: 1;
}

.auth-card {
  position: relative;
  width: min(860px, 100%);
  min-height: 480px;
  background: #eaeaea;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.22);
}

.auth-panel {
  position: absolute;
  top: 0;
  height: 100%;
  width: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.6s ease-in-out, opacity 0.45s ease;
  opacity: 1;
}

.auth-panel--form {
  background: #eaeaea;
  padding: 0 48px;
  box-sizing: border-box;
}

.auth-panel--signin {
  left: 0;
  z-index: 2;
}

.auth-panel--signup {
  left: 0;
  z-index: 1;
  opacity: 0;
}

.auth-card--signup .auth-panel--signin {
  transform: translateX(100%);
  opacity: 0;
  z-index: 1;
}

.auth-card--signup .auth-panel--signup {
  transform: translateX(100%);
  opacity: 1;
  z-index: 5;
}

.auth-form {
  width: 100%;
  max-width: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.auth-title {
  margin: 0 0 8px;
  font-size: 1.75rem;
  font-weight: 500;
  color: #333;
  letter-spacing: 0.02em;
}

.auth-input {
  width: 100%;
  height: 42px;
  padding: 0 14px;
  border: none;
  border-radius: 4px;
  background: #fff;
  color: #333;
  font-size: 0.95rem;
  outline: none;
  box-sizing: border-box;
  transition: box-shadow 0.2s ease;
}

.auth-input::placeholder {
  color: #aaa;
}

.auth-input:focus {
  box-shadow: 0 0 0 1px #222;
}

.auth-role {
  width: 100%;
  display: flex;
  gap: 20px;
  justify-content: center;
  font-size: 0.9rem;
  color: #555;
}

.auth-role__item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.auth-btn {
  min-width: 140px;
  height: 42px;
  margin-top: 6px;
  padding: 0 28px;
  border: none;
  border-radius: 999px;
  background: #008096;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s ease, opacity 0.2s ease;
}

.auth-btn:hover:not(:disabled) {
  background: #006d7f;
}

.auth-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.auth-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.auth-btn--ghost {
  background: transparent;
  border: 2px solid #fff;
}

.auth-btn--ghost:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.12);
}

.auth-overlay {
  position: absolute;
  top: 0;
  left: 50%;
  width: 50%;
  height: 100%;
  overflow: hidden;
  z-index: 2;
  transition: transform 0.6s ease-in-out;
}

.auth-card--signup .auth-overlay {
  transform: translateX(-100%);
}

.auth-overlay__inner {
  position: relative;
  left: -100%;
  width: 200%;
  height: 100%;
  transition: transform 0.6s ease-in-out;
}

.auth-overlay__inner::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('/images/auth-bg.png') center 42% / cover no-repeat;
  filter: saturate(0.55) brightness(0.96);
}

.auth-card--signup .auth-overlay__inner {
  transform: translateX(50%);
}

.auth-overlay__panel {
  position: absolute;
  top: 0;
  width: 50%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 40px;
  box-sizing: border-box;
  text-align: center;
  color: #fff;
}

.auth-overlay__panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(20, 45, 70, 0.32);
}

.auth-overlay__panel > * {
  position: relative;
  z-index: 1;
}

.auth-overlay__panel--left {
  left: 0;
}

.auth-overlay__panel--right {
  right: 0;
}

.auth-overlay__title {
  margin: 0 0 12px;
  font-size: 1.6rem;
  font-weight: 500;
}

.auth-overlay__text {
  margin: 0 0 24px;
  font-size: 0.95rem;
  line-height: 1.6;
  opacity: 0.92;
}

@media (max-width: 640px) {
  .auth-card {
    min-height: auto;
    display: flex;
    flex-direction: column;
  }

  .auth-panel,
  .auth-overlay {
    position: relative;
    width: 100%;
    left: auto;
    transform: none !important;
  }

  .auth-panel--form {
    padding: 32px 24px;
    order: 2;
  }

  .auth-panel--signup {
    display: none;
  }

  .auth-panel--signin {
    display: flex;
  }

  .auth-card--signup .auth-panel--signup {
    display: flex;
  }

  .auth-card--signup .auth-panel--signin {
    display: none;
  }

  .auth-overlay {
    order: 1;
    min-height: 200px;
  }

  .auth-overlay__inner {
    left: 0;
    width: 100%;
    transform: none !important;
  }

  .auth-overlay__panel {
    width: 100%;
    padding: 32px 24px;
  }

  .auth-overlay__panel--left {
    display: flex;
  }

  .auth-overlay__panel--right {
    display: none;
  }

  .auth-card--signup .auth-overlay__panel--left {
    display: none;
  }

  .auth-card--signup .auth-overlay__panel--right {
    display: flex;
  }
}
</style>
