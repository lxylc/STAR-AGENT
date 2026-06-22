import { ref } from 'vue'
import request from './request'

/** 与 localStorage 同步，供顶栏等组件响应式读取 */
const storedUserRef = ref(readUserFromStorage())

function readUserFromStorage() {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
}

export function login(data) {
  return request.post('/auth/login', data)
}

export function register(data) {
  return request.post('/auth/register', data)
}

export function getMe() {
  return request.get('/auth/me')
}

export function updateSettings(data) {
  return request.put('/auth/settings', data)
}

/** 管理员查看指定学生基础信息 */
export function getStudent(studentId) {
  return request.get(`/auth/students/${studentId}`)
}

/** 管理员修改指定学生基础信息 */
export function adminUpdateStudentSettings(studentId, data) {
  return request.put(`/auth/students/${studentId}/settings`, data)
}

export function listStudents(params) {
  const p = typeof params === 'string' ? { keyword: params } : params || {}
  return request.get('/auth/students', { params: p })
}

export function getToken() {
  return localStorage.getItem('token')
}

export function getStoredUser() {
  return storedUserRef.value
}

export function useStoredUser() {
  return storedUserRef
}

export function saveAuth(auth) {
  if (auth?.token) localStorage.setItem('token', auth.token)
  if (auth) localStorage.setItem('user', JSON.stringify(auth))
  storedUserRef.value = readUserFromStorage()
}

export function clearAuth() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  storedUserRef.value = null
}

export function getStudentId() {
  const u = getStoredUser()
  return u?.studentId ?? null
}
