import request from './request'

export function getMasteryStatus(studentId, subject) {
  return request.get('/knowledge/mastery', { params: { studentId, subject } })
}
