<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h2>注册</h2>
      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.realName" placeholder="可选" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">注册</el-button>
        <div class="foot">
          已有账号？<router-link to="/login">登录</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register, saveAuth } from '../api/auth'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '', realName: '' })

async function onSubmit() {
  loading.value = true
  try {
    const auth = await register(form)
    saveAuth(auth)
    ElMessage.success('注册成功')
    router.push('/chat')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}
.auth-card { width: 400px; }
.foot { margin-top: 16px; text-align: center; color: #666; }
</style>
