import axios from 'axios'
import request from './request'

const profileClient = axios.create({
  baseURL: '/profile-api',
  timeout: 15000
})

/** Java 后端埋点（需登录） */
export function trackBehaviorJava(data) {
  return request.post('/behavior/track', data).catch(() => null)
}

/** Flask 后端埋点 */
export function trackBehaviorFlask(data) {
  return profileClient.post('/api/profile-build/behavior/track', data).catch(() => null)
}

/** 双写埋点（Flask + Java，失败静默） */
export function trackBehavior(studentId, eventType, payload = {}, source = 'frontend') {
  const javaBody = { studentId, eventType, eventSource: source, payload }
  const flaskBody = { student_id: studentId, event_type: eventType, event_source: source, payload }
  trackBehaviorFlask(flaskBody)
  trackBehaviorJava(javaBody)
}
