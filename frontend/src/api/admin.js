import axios from 'axios'
import request from './request'

const profileClient = axios.create({
  baseURL: '/profile-api',
  timeout: 120000
})

/** 获取班级学情总览（四卡片 + 模块均分） */
export function getClassOverview(studentIds) {
  return profileClient
    .post('/api/profile-build/admin/class-overview', { student_ids: studentIds })
    .then((r) => r.data)
}

/** 批量获取学生学情均分与活跃时间 */
export function getStudentsStats(studentIds) {
  return profileClient
    .post('/api/profile-build/admin/students-stats', { student_ids: studentIds })
    .then((r) => r.data)
}

/** 重置单个学生密码 */
export function resetStudentPassword(studentId) {
  return request.post(`/auth/students/${studentId}/reset-password`)
}

/** 批量重置密码 */
export function batchResetPassword(studentIds, newPassword) {
  return request.post('/auth/students/batch-reset-password', {
    studentIds,
    newPassword
  })
}

/** 启用/禁用学生账号 */
export function setStudentStatus(studentId, enabled) {
  return request.put(`/auth/students/${studentId}/status`, { enabled })
}

/** 导出 CSV（Excel 兼容） */
export function exportStudentsCsv(rows, filename = '全班学情报表.csv') {
  if (!rows.length) return
  const headers = ['ID', '用户名', '姓名', '年级', '专业', '整体学情均分', '最近活跃时间', '账号状态']
  const lines = [
    headers.join(','),
    ...rows.map((r) =>
      [
        r.id,
        `"${(r.username || '').replace(/"/g, '""')}"`,
        `"${(r.realName || '').replace(/"/g, '""')}"`,
        `"${(r.grade || '').replace(/"/g, '""')}"`,
        `"${(r.major || '').replace(/"/g, '""')}"`,
        r.avgScore ?? '-',
        r.lastActiveAt || '-',
        r.enabled === false ? '禁用' : '启用'
      ].join(',')
    )
  ]
  const bom = '\uFEFF'
  const blob = new Blob([bom + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
