import axios from 'axios'

const client = axios.create({
  baseURL: '/profile-api',
  timeout: 180000
})

export function getEvaluationMetrics(studentId, courseId) {
  return client
    .get(`/api/profile-build/evaluation/metrics/${studentId}`, {
      params: courseId ? { course_id: courseId } : {}
    })
    .then((r) => r.data)
}

export function generateEvaluation(payload) {
  return client.post('/api/profile-build/evaluation/generate', payload).then((r) => r.data)
}

export function listEvaluations(studentId, limit = 10) {
  return client
    .get(`/api/profile-build/evaluation/list/${studentId}`, { params: { limit } })
    .then((r) => r.data)
}

export function getEvaluationDetail(evalId) {
  return client.get(`/api/profile-build/evaluation/${evalId}`).then((r) => r.data)
}

export function previewEvaluationAdjustment(adjustment) {
  return client
    .post('/api/profile-build/evaluation/adjustment-preview', { adjustment })
    .then((r) => r.data)
}

export function syncEvaluationApply(payload) {
  return client.post('/api/profile-build/evaluation/apply-sync', payload).then((r) => r.data)
}

export function getEvaluationApplyLog(studentId) {
  return client.get(`/api/profile-build/evaluation/apply-log/${studentId}`).then((r) => r.data)
}
