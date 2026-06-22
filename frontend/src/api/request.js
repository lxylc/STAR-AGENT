import axios from 'axios'
import { ElMessage } from 'element-plus'
import { clearAuth } from './auth'

const request = axios.create({
  baseURL: '/api',
  timeout: 120000
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body.code !== 200) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body.data
  },
  (err) => {
    if (err.response?.status === 401) {
      clearAuth()
      const path = window.location.pathname
      if (!path.startsWith('/login') && !path.startsWith('/register')) {
        window.location.href = '/login'
      }
    }
    ElMessage.error(err.response?.data?.message || err.message || '网络异常')
    return Promise.reject(err)
  }
)

export default request
