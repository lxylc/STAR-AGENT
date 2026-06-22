import axios from 'axios'

/** 公开演示接口，无需登录 */
const client = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export const PUBLIC_DEMO_STUDENT_ID = 1

export function getPublicDemoProfile(studentId = PUBLIC_DEMO_STUDENT_ID) {
  return client.get(`/public/demo/profile/${studentId}`).then((r) => r.data.data)
}
