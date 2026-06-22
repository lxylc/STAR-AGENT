import request from './request'
import { getStudentId } from './auth'

/** @deprecated 请使用 getStudentId() */
export const DEMO_STUDENT_ID = getStudentId() || 1

/** @deprecated 已由 Flask /api/profile-build 对话流程替代，前端未使用 */
export function initDialogue(studentId) {
  return request.post(`/profile/dialogue/init/${studentId}`)
}

/** @deprecated */
export function sendDialogue(data) {
  return request.post('/profile/dialogue/send', data)
}

/** @deprecated */
export function getDialogueHistory(studentId) {
  return request.get(`/profile/dialogue/history/${studentId}`)
}

/** @deprecated */
export function extractProfile(studentId) {
  return request.post(`/profile/dialogue/extract/${studentId}`)
}

export function getProfile(studentId) {
  return request.get(`/profile/${studentId}`)
}

export function updateProfile(data) {
  return request.put('/profile', data)
}
