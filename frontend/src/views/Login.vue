<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h2>登录</h2>
      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" autocomplete="current-password" show-password />
        </el-form-item>
        <el-form-item label="身份">
          <el-radio-group v-model="form.role">
            <el-radio value="student">学生</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">登录</el-button>
        <div class="foot">
          还没有账号？<router-link to="/register">注册</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, saveAuth, getStudentId } from '../api/auth'
import { trackBehavior } from '../api/behavior'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '', role: 'student' })

async function onSubmit() {
  loading.value = true
  try {
    const auth = await login(form)
    saveAuth(auth)
    const sid = auth.studentId || getStudentId()
    if (sid) trackBehavior(sid, 'login', { username: auth.username })
    ElMessage.success('登录成功')
    router.push(auth.role === 'admin' ? '/admin/students' : '/chat')
  } finally {
    loading.value = false
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
  /* 将 login-bg.jpg 放到 frontend/public/images/ 即可生效 */
  background-color: #1e3a5f;
  background-image: url('/images/login-bg.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

/* 半透明遮罩，保证登录卡片文字清晰 */
.auth-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(15, 35, 65, 0.45);
  pointer-events: none;
}

.auth-card {
  position: relative;
  z-index: 1;
  width: 400px;
}

.foot {
  margin-top: 16px;
  text-align: center;
  color: #666;
}
</style>
