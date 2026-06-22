import axios from 'axios'

/** Flask 画像构建服务（Vite 代理 /profile-api） */
const client = axios.create({
  baseURL: '/profile-api',
  timeout: 120000
})

export const DEMO_STUDENT_ID = 1

/** 初始化对话（欢迎语 + 开始按钮） */
export function initBuildDialogue(studentId) {
  return client.post(`/api/profile-build/dialogue/init/${studentId}`).then((r) => r.data)
}

/** 重新构建：清空掌握数据 + 新会话 */
export function rebuildProfile(studentId) {
  return client.post(`/api/profile-build/dialogue/rebuild/${studentId}`).then((r) => r.data)
}

export function submitDialogueText(payload) {
  return client.post('/api/profile-build/dialogue/text-submit', payload).then((r) => r.data)
}

/** 对话分步：点击内嵌选项后提交 */
export function submitDialogueStep(payload) {
  return client.post('/api/profile-build/dialogue/step-submit', payload).then((r) => r.data)
}

export function getBuildDialogueHistory(studentId, sessionId) {
  return client
    .get(`/api/profile-build/dialogue/history/${studentId}`, {
      params: sessionId ? { session_id: sessionId } : {}
    })
    .then((r) => r.data)
}

export function getModuleMastery(studentId) {
  return client.get(`/api/profile-build/mastery/${studentId}`).then((r) => r.data)
}

export function getBuildProfile(studentId) {
  return client.get(`/api/profile-build/profile/${studentId}`).then((r) => r.data)
}

export function updateKpLevel(payload) {
  return client.post('/api/profile-build/profile/update', payload).then((r) => r.data)
}

/** 日常答疑 */
export function initQaDialogue(studentId) {
  return client.post(`/api/profile-build/qa/init/${studentId}`).then((r) => r.data)
}

export function askQaQuestion(payload) {
  return client.post('/api/profile-build/qa/ask', payload).then((r) => r.data)
}

export function getQaHistory(studentId) {
  return client.get(`/api/profile-build/qa/history/${studentId}`).then((r) => r.data)
}

/** 学情分析：编排专属资源生成计划 */
export function getResourcePlan(payload) {
  return client.post('/api/profile-build/resources/plan', payload).then((r) => r.data)
}

/** 标签跳转学习页（POST） */
export function navigateByTag(payload) {
  return client.post('/api/profile-build/tag/navigate', payload).then((r) => r.data)
}

/** 学习专区/训练页按 query 拉取跳转数据（GET） */
export function getTagNavigateData(params) {
  return client.get('/api/profile-build/tag/navigate', { params }).then((r) => r.data)
}

/** 模块练习：题库智能体实时出题 */
export function generateModulePractice(payload) {
  return client.post('/api/profile-build/practice/generate', payload).then((r) => r.data)
}

/** 模块练习：提交批改并回写画像 */
export function submitModulePractice(payload) {
  return client.post('/api/profile-build/practice/submit', payload).then((r) => r.data)
}

/** 聚合学习历史 */
export function getLearningHistory(studentId) {
  return client.get(`/api/profile-build/history/all/${studentId}`).then((r) => r.data)
}

/** 错题复习列表 */
export function getWrongQuestions(studentId, limit = 100) {
  return client
    .get(`/api/profile-build/wrong-questions/${studentId}`, { params: { limit } })
    .then((r) => r.data)
}

export function markWrongReviewed(payload) {
  return client.post('/api/profile-build/wrong-questions/reviewed', payload).then((r) => r.data)
}

/** 统一习题中心 */
export function getExerciseCenterOverview(studentId) {
  return client.get(`/api/profile-build/exercise-center/overview/${studentId}`).then((r) => r.data)
}

export function generateExerciseSession(payload) {
  return client.post('/api/profile-build/exercise-center/generate', payload).then((r) => r.data)
}

export function submitExerciseSession(payload) {
  return client.post('/api/profile-build/exercise-center/submit', payload).then((r) => r.data)
}

/** 学习路线进度 */
export function getRoadmapProgress(studentId, params = {}) {
  return client
    .get(`/api/profile-build/roadmap/progress/${studentId}`, { params })
    .then((r) => r.data)
}

export function updateRoadmapTask(payload) {
  return client.post('/api/profile-build/roadmap/task', payload).then((r) => r.data)
}

export function advanceRoadmapStage(payload) {
  return client.post('/api/profile-build/roadmap/advance', payload).then((r) => r.data)
}

export function getResourceStatusMap(studentId, resourceIds = []) {
  const params = resourceIds.length ? { ids: resourceIds.join(',') } : {}
  return client.get(`/api/profile-build/resource-status/${studentId}`, { params }).then((r) => r.data)
}

export function markResourceStatus(payload) {
  return client.post('/api/profile-build/resource-status/mark', payload).then((r) => r.data)
}

/** 代码案例运行（仅执行，不判题） */
export function runPythonCode(payload) {
  return client.post('/api/profile-build/code/run', payload).then((r) => r.data)
}

/** 代码实操验收：运行 + 逐项测试 */
export function checkCodePractice(payload) {
  return client.post('/api/profile-build/code/check', payload).then((r) => r.data)
}

/** 代码实操提交：验收通过后回写画像 */
export function submitCodePractice(payload) {
  return client
    .post('/api/profile-build/code/submit', payload)
    .then((r) => r.data)
    .catch((err) => {
      if (err.response?.data) return err.response.data
      return Promise.reject(err)
    })
}
