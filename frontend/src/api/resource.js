import request from './request'
import { DEMO_STUDENT_ID } from './profile'

export { DEMO_STUDENT_ID }

export function generateResource(data) {
  return request.post('/resource/generate', data, { timeout: 300000 })
}

export function listResources(params) {
  return request.get('/resource/list', { params })
}

export function getResource(id) {
  return request.get(`/resource/${id}`)
}

export function getTaskDetail(taskId) {
  return request.get(`/resource/task/${taskId}`)
}

export function listTasks(studentId) {
  return request.get('/resource/tasks', { params: { studentId } })
}
