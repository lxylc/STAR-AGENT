import axios from 'axios'

const client = axios.create({
  baseURL: '/profile-api',
  timeout: 180000
})

export function initTutoring(studentId, sessionId) {
  const payload = sessionId ? { session_id: sessionId } : {}
  return client.post(`/api/profile-build/tutoring/init/${studentId}`, payload).then((r) => r.data)
}

export function createTutoringSession(studentId) {
  return client.post(`/api/profile-build/tutoring/new-session/${studentId}`).then((r) => r.data)
}

export function askTutoring(payload) {
  return client.post('/api/profile-build/tutoring/ask', payload).then((r) => r.data)
}

export function getTutoringHistory(studentId) {
  return client.get(`/api/profile-build/tutoring/history/${studentId}`).then((r) => r.data)
}

/** 调用讯飞文生图 + TTS 生成真实图片与语音 */
export function generateTutoringMedia(payload) {
  return client.post('/api/profile-build/tutoring/generate-media', payload, {
    timeout: 300000
  }).then((r) => r.data)
}
