import request from './request'
import { DEMO_STUDENT_ID } from './profile'

export { DEMO_STUDENT_ID }

export function getKnowledgeGraph(subject) {
  return request.get('/knowledge/graph', { params: { subject } })
}

export function planPath(data) {
  return request.post('/path/plan', data, { timeout: 300000 })
}

export function replanPath(pathId) {
  return request.post(`/path/replan/${pathId}`, null, { timeout: 300000 })
}

export function getActivePath(studentId, subject) {
  return request.get('/path/active', { params: { studentId, subject } })
}

export function refreshPush(pathId) {
  return request.post(`/path/${pathId}/refresh-push`)
}

export function updateProgress(data) {
  return request.put('/progress/update', data)
}

export function listProgress(studentId, subject) {
  return request.get('/progress/list', { params: { studentId, subject } })
}

export function listPush(studentId, readStatus) {
  return request.get('/push/list', { params: { studentId, readStatus } })
}

export function markPushRead(id) {
  return request.put(`/push/${id}/read`)
}

export function applyEvaluationAdjustments(data) {
  return request.post('/path/apply-evaluation', data, { timeout: 120000 })
}

export function syncPathFromProfile(data) {
  return request.post('/path/sync-from-profile', data, { timeout: 60000 })
}
