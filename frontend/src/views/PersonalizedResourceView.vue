<template>
  <div class="personalized-page">
    <ProfileRequiredAlert :loading="profileLoading" :profile-completed="profileCompleted" />

    <template v-if="profileCompleted">
      <el-card shadow="never" class="flow-card">
        <div class="flow-steps">
          <span class="flow-step" @click="$router.push('/profile/view')">① 用户画像</span>
          <span class="flow-arrow">→</span>
          <span class="flow-step" @click="$router.push('/evaluation')">② 学习效果评估</span>
          <span class="flow-arrow">→</span>
          <span class="flow-step flow-step--active">③ 学习资源</span>
        </div>
      </el-card>

      <el-card shadow="never" class="summary-card">
        <template #header>
          <div class="head-row">
            <span>个性化学习资源</span>
            <el-button link type="primary" @click="$router.push('/profile/view')">用户画像</el-button>
          </div>
        </template>

        <div v-loading="planLoading" class="summary-body">
          <div v-if="plan?.basis" class="basis-card">
            <h4 class="basis-title">资源生成依据</h4>

            <div class="basis-section">
              <h5 class="basis-subtitle">实时画像来源</h5>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="模块平均分">
                  {{ plan.basis.avg_score ?? '—' }} 分
                </el-descriptions-item>
              </el-descriptions>
              <p class="basis-hint">
                学习行为实时更新画像，驱动学情推荐；原生薄弱：{{
                  (plan.basis.profile_weak_modules || []).join('、') || '暂无'
                }}
              </p>
            </div>

            <div class="basis-section">
              <h5 class="basis-subtitle">评估联动补强</h5>
              <template v-if="plan.basis.evaluation_adjusted">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="评估新增薄弱">
                    {{ (plan.basis.evaluation_focus_modules || []).join('、') }}
                  </el-descriptions-item>
                  <el-descriptions-item
                    v-if="plan.basis.evaluation_focus_modules?.length > (plan.basis.batch_eval_count ?? 0)"
                    label="本批覆盖"
                  >
                    评估薄弱 {{ plan.basis.evaluation_focus_modules.length }} 个，本批覆盖
                    {{ plan.module_plans?.length || 0 }} 个（评估补强
                    {{ plan.basis.batch_eval_count ?? 0 }} 个）
                  </el-descriptions-item>
                  <el-descriptions-item
                    v-if="plan.basis.prefer_resource_types?.length"
                    label="优先资源类型"
                  >
                    {{ preferTypeLabels.join('、') }}
                  </el-descriptions-item>
                </el-descriptions>
              </template>
              <p v-else class="basis-empty">
                尚未应用评估调整，可前往
                <el-button link type="primary" @click="$router.push('/evaluation')">学习效果评估</el-button>
                生成并应用方案
              </p>
            </div>

            <div v-if="recommendSummary" class="recommend-block">
              <h5 class="basis-subtitle">本批推荐理由</h5>
              <p class="recommend-summary">{{ recommendSummary }}</p>
            </div>
            <p v-if="plan?.summary_line" class="summary-line">{{ plan.summary_line }}</p>
          </div>

          <div v-if="pushModes.length" class="push-modes">
            <div v-for="m in pushModes" :key="m.key" class="push-mode-item">
              <strong>{{ m.title }}</strong>
              <span>{{ m.desc }}</span>
            </div>
          </div>

          <div class="action-row">
            <el-tooltip placement="top" :show-after="300">
              <template #content>
                调用星火多智能体流水线：讲义智能体（LECTURE）→ 习题智能体（EXERCISE）→
                课件智能体（COURSEWARE），按薄弱模块分工生成定制资源。
              </template>
              <el-button type="primary" :loading="generating" :disabled="planLoading" @click="runGenerate">
                {{ generating ? '星火生成中（约1–3分钟/模块）…' : '星火 AI 深度生成' }}
              </el-button>
            </el-tooltip>
            <el-tooltip placement="top" :show-after="300">
              <template #content>
                按当前 Tab 类型调用星火智能体，为本批薄弱模块重新生成{{ tabTypeLabel }}（不刷新计划排序）
              </template>
              <el-button
                :loading="regenerating"
                :disabled="planLoading || generating"
                @click="regenerateByTabType"
              >
                {{ regenerateButtonLabel }}
              </el-button>
            </el-tooltip>
          </div>

          <el-alert
            v-if="generateError"
            :title="generateError"
            type="warning"
            :closable="false"
            show-icon
            class="task-alert"
          />
          <el-alert
            v-if="lastTask"
            :title="`最近任务 #${lastTask.task?.id} · ${lastTask.task?.taskStatus}`"
            type="success"
            :closable="false"
            show-icon
            class="task-alert"
          />
        </div>
      </el-card>

      <el-row :gutter="12" class="stats-row">
        <el-col :span="6">
          <div class="stat-card">
            <span class="stat-num">{{ resourceStats.total }}</span>
            <span class="stat-label">推荐总资源</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-card--eval">
            <span class="stat-num">{{ resourceStats.eval }}</span>
            <span class="stat-label">评估补强</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-card--profile">
            <span class="stat-num">{{ resourceStats.profile }}</span>
            <span class="stat-label">学情推荐</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card stat-card--ai">
            <span class="stat-num">{{ resourceStats.ai }}</span>
            <span class="stat-label">AI 生成</span>
          </div>
        </el-col>
      </el-row>

      <el-card shadow="never" class="tabs-card">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="知识点讲义" name="knowledge">
            <div v-loading="loading" class="tab-body">
              <PersonalizedResourceCard
                :items="tabKnowledge"
                :status-map="statusMap"
                show-mark-viewed
                @open="openDetail"
                @mark-viewed="markLectureViewed"
              />
            </div>
          </el-tab-pane>
          <el-tab-pane label="优秀代码案例" name="code">
            <div v-loading="loading" class="tab-body">
              <p class="tab-hint">根据学情推荐规范写法与优秀实现，供观看学习；可在列表或学习路径中直接「标记已阅」。</p>
              <PersonalizedResourceCard
                :items="tabCode"
                :status-map="statusMap"
                show-copy
                show-mark-viewed
                @open="openDetail"
                @copy="copyCode"
                @mark-viewed="(row) => markCodeViewed(row, { completeRoadmapTask: true })"
              />
            </div>
          </el-tab-pane>
          <el-tab-pane label="专项习题" name="exam">
            <div v-loading="loading" class="tab-body">
              <p class="tab-hint">
                专项习题在「星火 AI 深度生成」时一并产出；同一批题可反复练习，点击「更新习题」或再次深度生成会换新题。
              </p>
              <PersonalizedResourceCard :items="tabExam" :status-map="statusMap" @open="openDetail" />
              <el-button
                v-if="primaryModuleId"
                type="primary"
                class="practice-link"
                @click="goExerciseCenter('special')"
              >
                前往习题中心做题 →
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="学习路径 & 拓展" name="extra">
            <div class="tab-body extra-body" v-loading="roadmapLoading">
              <el-alert
                type="info"
                :closable="false"
                show-icon
                class="roadmap-hint"
                title="学习路径说明"
                :description="plan?.roadmap_hint || '按学情顺序推送任务：完成一项后自动显示下一项；本模块三项全部完成后进入下一薄弱模块。'"
              />
              <div v-if="roadmapProgress" class="roadmap-progress-bar">
                <span>
                  路径进度：已完成 {{ roadmapProgress.completed_stages ?? roadmapProgress.completed_days }} 个阶段
                  <template v-if="currentStage && !stageAllDone">
                    · 本模块 {{ currentStage.tasks_completed_count ?? 0 }}/{{ currentStage.tasks_total ?? 3 }} 项
                  </template>
                </span>
                <el-progress
                  :percentage="roadmapPercent"
                  :stroke-width="8"
                  :show-text="false"
                  class="progress-line"
                />
              </div>
              <p v-if="roadmapStageCompleteHint" class="day-complete-hint">{{ roadmapStageCompleteHint }}</p>
              <div v-if="currentStage && activeTask" class="roadmap">
                <div class="roadmap-day">
                  <div class="day-head">
                    <h4>当前任务 · {{ currentStage.module_name }}</h4>
                    <p class="stage-sub">
                      第 {{ currentStage.stage || currentStage.day }} 阶段 ·
                      任务 {{ activeTask.order || activeTaskIndex }}/{{ currentStage.tasks_total || 3 }}
                    </p>
                  </div>
                  <div v-if="completedTasksInStage.length" class="done-steps">
                    <span
                      v-for="t in completedTasksInStage"
                      :key="t.id"
                      class="done-step"
                    >
                      ✓ {{ taskTypeLabel(t.type) }}
                    </span>
                  </div>
                  <div class="task-current">
                    <div class="task-current-head">
                      <span class="task-current-label">进行中</span>
                      <el-tag size="small" type="warning">{{ taskTypeLabel(activeTask.type) }}</el-tag>
                    </div>
                    <p class="task-current-title">{{ activeTask.title }}</p>
                    <div class="task-current-actions">
                      <el-button
                        v-if="activeTask.type === 'lecture'"
                        type="primary"
                        size="small"
                        @click="openLectureForDay(currentStage)"
                      >
                        打开讲义
                      </el-button>
                      <el-button
                        v-if="activeTask.type === 'exercise' && currentStage.module_id"
                        type="primary"
                        size="small"
                        @click="goRoadmapExercise(currentStage)"
                      >
                        去做题
                      </el-button>
                      <el-button
                        v-if="activeTask.type === 'code' && currentStage.module_id"
                        type="primary"
                        size="small"
                        @click="openCodeForDay(currentStage)"
                      >
                        观看案例
                      </el-button>
                      <el-button
                        v-if="activeTask.type === 'lecture'"
                        size="small"
                        @click="markLectureCompleteForStage(currentStage, activeTask)"
                      >
                        标记已阅
                      </el-button>
                      <el-button
                        v-if="activeTask.type === 'code'"
                        size="small"
                        @click="markCodeViewedForStage(currentStage, activeTask)"
                      >
                        标记已阅
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else-if="currentStage && stageAllDone" class="roadmap">
                <el-result icon="success" title="本模块任务已全部完成">
                  <template #sub-title>
                    <span v-if="roadmapProgress?.advanced || roadmapStageCompleteHint">
                      {{ roadmapStageCompleteHint || '已自动进入下一薄弱模块，请点击「更新习题」获取新题目。' }}
                    </span>
                    <span v-else>点击「更新习题」为本批薄弱模块重新生成题目。</span>
                  </template>
                  <template #extra>
                    <el-button type="primary" @click="regenerateByTabType">更新习题</el-button>
                  </template>
                </el-result>
              </div>
              <div v-if="roadmapHistory.length" class="history-block">
                <h4 class="block-title">已完成阶段</h4>
                <ul class="history-list">
                  <li v-for="h in roadmapHistory" :key="h.stage_no">
                    第 {{ h.stage_no }} 阶段 · {{ h.module_name }}
                  </li>
                </ul>
              </div>
              <el-empty
                v-if="!planLoading && !roadmapLoading && !currentStage && !plan?.tips?.length"
                description="暂无当前任务，请刷新学情计划"
              >
                <el-button type="primary" @click="refreshAll">刷新计划</el-button>
              </el-empty>
              <div v-if="plan?.tips?.length" class="tips-block">
                <h4 class="block-title">学习小贴士 <el-tag size="small" type="info">拓展自选</el-tag></h4>
                <ul class="tips-list">
                  <li v-for="(tip, i) in plan.tips" :key="i">{{ tip }}</li>
                </ul>
              </div>
              <div v-if="plan?.external_links?.length" class="links-block">
                <h4 class="block-title">拓展链接 <el-tag size="small" type="info">拓展自选</el-tag></h4>
                <ul class="link-list">
                  <li v-for="link in plan.external_links" :key="link.url">
                    <a :href="link.url" target="_blank" rel="noopener">{{ link.title }}</a>
                  </li>
                </ul>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <ResourceDetailDrawer
        v-model:visible="drawerVisible"
        :resource="current"
        :student-id="studentId"
        :status-map="statusMap"
        @status-change="onStatusChange"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import ResourceDetailDrawer from '../components/ResourceDetailDrawer.vue'
import PersonalizedResourceCard from '../components/PersonalizedResourceCard.vue'
import ProfileRequiredAlert from '../components/ProfileRequiredAlert.vue'
import { useRequiresProfile } from '../composables/useRequiresProfile'
import { extractCodeBlock } from '../utils/markdown'
import {
  sortPersonalizedResources,
  enrichAiResource,
  buildRecommendSummary,
  countByTier
} from '../utils/personalizedResource'
import {
  getResourcePlan,
  getRoadmapProgress,
  updateRoadmapTask,
  getResourceStatusMap,
  markResourceStatus
} from '../api/profileBuild'
import { generateResource, listResources } from '../api/resource'
import { getStudentId, getToken } from '../api/auth'
import { trackBehavior } from '../api/behavior'
import { DEMO_STUDENT_ID } from '../api/profile'
import { COURSE_NAME } from '../constants/course'

const TYPE_LABELS = { lecture: '讲义', exercise: '习题', courseware: '代码案例', exam_summary: '考点' }
const PREFER_LABELS = { lecture: '讲义', exercise: '习题', courseware: '课件', exam_summary: '考点' }
const TAB_AGENT_TYPES = {
  knowledge: ['LECTURE'],
  code: ['COURSEWARE'],
  exam: ['EXERCISE'],
  extra: ['EXERCISE']
}
const TAB_TYPE_LABELS = {
  knowledge: '讲义',
  code: '代码案例',
  exam: '习题',
  extra: '习题'
}

const route = useRoute()
const router = useRouter()
const { loading: profileLoading, profileCompleted } = useRequiresProfile()
const studentId = getStudentId() || DEMO_STUDENT_ID
const planLoading = ref(false)
const roadmapLoading = ref(false)
const loading = ref(false)
const generating = ref(false)
const regenerating = ref(false)
const plan = ref(null)
const roadmapProgress = ref(null)
const resources = ref([])
const lastTask = ref(null)
const generateError = ref('')
const activeTab = ref('extra')
const drawerVisible = ref(false)
const current = ref(null)
const roadmapStageCompleteHint = ref('')
const newAiCount = ref(0)
const statusMap = ref({})

const moduleId = computed(() => {
  const q = route.query.moduleId
  return q ? Number(q) : null
})

const bundleMode = computed(() => route.query.bundleMode || 'weak_bundle')

const pushModes = computed(() => plan.value?.push_modes || [])

const tabTypeLabel = computed(() => TAB_TYPE_LABELS[activeTab.value] || '资源')

const regenerateButtonLabel = computed(() => {
  if (regenerating.value) return `更新${tabTypeLabel.value}中…`
  return `更新${tabTypeLabel.value}`
})

const preferTypeLabels = computed(() =>
  (plan.value?.basis?.prefer_resource_types || []).map((t) => PREFER_LABELS[t] || t)
)

const recommendSummary = computed(() =>
  plan.value?.recommend_summary || buildRecommendSummary(plan.value)
)

const sortedResources = computed(() => {
  const previews = (plan.value?.preview_resources || []).map((r) => ({
    ...r,
    resourceType: r.resourceType || r.resource_type
  }))
  const merged = [...previews]
  const seen = new Set(previews.map((r) => r.id))
  for (const r of resources.value) {
    if (!seen.has(r.id)) {
      merged.push(enrichAiResource(r, plan.value))
    }
  }
  if (newAiCount.value > 0) {
    const aiItems = merged.filter((r) => !r.preview)
    const others = merged.filter((r) => r.preview)
    aiItems.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    return sortPersonalizedResources([...aiItems.slice(0, newAiCount.value), ...aiItems.slice(newAiCount.value), ...others])
  }
  return sortPersonalizedResources(merged)
})

const resourceStats = computed(() => countByTier(sortedResources.value))

function categorize(list) {
  const knowledge = []
  const code = []
  const exam = []
  for (const r of list) {
    const t = r.resourceType
    if (t === 'lecture' || t === 'exam_summary') knowledge.push(r)
    else if (t === 'courseware') code.push(r)
    else if (t === 'exercise') exam.push(r)
    else knowledge.push(r)
  }
  return { knowledge, code, exam }
}

const tabKnowledge = computed(() => categorize(sortedResources.value).knowledge)
const tabCode = computed(() => categorize(sortedResources.value).code)
const tabExam = computed(() => {
  let exam = categorize(sortedResources.value).exam
  const aiModuleIds = new Set(
    exam.filter((r) => (r.contentJson || r.content_json) && !r.preview).map((r) => Number(r.module_id))
  )
  exam = exam.filter(
    (r) => !(r.preview && r.pending_generate && aiModuleIds.has(Number(r.module_id)))
  )
  return exam.sort((a, b) => {
    const score = (r) => ((r.contentJson || r.content_json) && !r.preview ? 0 : 1)
    return score(a) - score(b)
  })
})

const primaryModuleId = computed(() => plan.value?.module_plans?.[0]?.module_id || moduleId.value)

const currentStage = computed(
  () =>
    roadmapProgress.value?.current_stage ||
    roadmapProgress.value?.current ||
    plan.value?.roadmap?.[0] ||
    null
)

const activeTask = computed(() => {
  const stage = currentStage.value
  if (stage?.active_task) return stage.active_task
  return (stage?.tasks || []).find((t) => !t.completed) || null
})

const activeTaskIndex = computed(() => {
  const t = activeTask.value
  if (t?.order) return t.order
  const tasks = currentStage.value?.tasks || []
  const idx = tasks.findIndex((x) => x.id === t?.id)
  return idx >= 0 ? idx + 1 : 1
})

const completedTasksInStage = computed(() =>
  (currentStage.value?.tasks || []).filter((t) => t.completed)
)

const stageAllDone = computed(
  () =>
    Boolean(currentStage.value?.stage_completed || currentStage.value?.day_completed) &&
    !activeTask.value
)

const roadmapHistory = computed(() => roadmapProgress.value?.history || [])

const roadmapDays = computed(() => {
  const cur = roadmapProgress.value?.current_stage || roadmapProgress.value?.current
  return cur ? [cur] : plan.value?.roadmap || []
})

const roadmapPercent = computed(() => {
  const completed = roadmapProgress.value?.completed_stages ?? roadmapProgress.value?.completed_days ?? 0
  const total = completed + (currentStage.value && !(currentStage.value.stage_completed || currentStage.value.day_completed) ? 1 : 0)
  return total ? Math.round((completed / total) * 100) : 0
})

function taskTypeLabel(type) {
  return { lecture: '讲义', code: '代码', exercise: '习题', text: '任务' }[type] || type
}

function applyDefaultTab() {
  const hasEval = (plan.value?.basis?.evaluation_focus_modules || []).length > 0
  activeTab.value = hasEval ? 'knowledge' : 'extra'
}

function findResourceForDay(day, type) {
  const list = sortedResources.value
  return list.find(
    (r) =>
      Number(r.module_id) === Number(day.module_id) &&
      (type === 'lecture'
        ? r.resourceType === 'lecture' || r.resourceType === 'exam_summary'
        : r.resourceType === 'courseware')
  )
}

function openLectureForDay(day) {
  const row = findResourceForDay(day, 'lecture')
  if (row) openDetail(row)
  else {
    activeTab.value = 'knowledge'
    ElMessage.info('请在本页讲义列表中选择对应模块资源（需手动勾选任务完成）')
  }
}

function openCodeForDay(day) {
  const row = findResourceForDay(day, 'code')
  if (row) openDetail(row)
  else activeTab.value = 'code'
}

async function loadRoadmapProgress() {
  roadmapLoading.value = true
  try {
    roadmapProgress.value = await getRoadmapProgress(studentId)
  } catch {
    roadmapProgress.value = null
  } finally {
    roadmapLoading.value = false
  }
}

async function loadResourceStatus() {
  const ids = sortedResources.value.map((r) => String(r.id)).filter(Boolean)
  if (!ids.length) {
    statusMap.value = {}
    return
  }
  try {
    statusMap.value = await getResourceStatusMap(studentId, ids)
  } catch {
    statusMap.value = {}
  }
}

function onStatusChange(payload) {
  if (!payload?.resource_id) return
  statusMap.value = {
    ...statusMap.value,
    [payload.resource_id]: { ...statusMap.value[payload.resource_id], status: payload.status }
  }
}

async function markResourceViewed(row) {
  if (!row?.id) return false
  try {
    await markResourceStatus({
      student_id: studentId,
      resource_id: String(row.id),
      status: 'viewed',
      resource_type: row.resourceType,
      module_id: row.module_id
    })
    onStatusChange({ resource_id: String(row.id), status: 'viewed' })
    trackBehavior(studentId, 'resource_mark_viewed', {
      resource_id: row.id,
      resource_type: row.resourceType,
      module_id: row.module_id
    })
    return true
  } catch (e) {
    const msg = e?.response?.data?.error || e?.message
    ElMessage.error(msg ? `标记失败：${msg}` : '标记失败，请稍后重试')
    return false
  }
}

async function completeRoadmapTaskIfMatch(moduleIdFromRow, taskType) {
  const stage = currentStage.value
  if (!stage || Number(stage.module_id) !== Number(moduleIdFromRow)) return
  const task =
    activeTask.value?.type === taskType
      ? activeTask.value
      : stage.tasks?.find((t) => t.type === taskType && !t.completed)
  if (task && !task.completed) {
    await toggleTask(stage, task, true)
  }
}

async function markLectureViewed(row) {
  if (!(await markResourceViewed(row))) return
  ElMessage.success('已标记为已阅')
  await completeRoadmapTaskIfMatch(row.module_id, 'lecture')
}

async function markLectureCompleteForStage(stage, task) {
  const row = findResourceForDay(stage, 'lecture')
  if (row) {
    if (!(await markResourceViewed(row))) return
    ElMessage.success('已标记为已阅')
  } else if (task && !task.completed) {
    await toggleTask(stage, task, true)
    ElMessage.success('任务已完成')
    return
  }
  if (task && !task.completed) {
    await toggleTask(stage, task, true)
  }
}

async function markCodeViewed(row, { completeRoadmapTask = false } = {}) {
  if (!(await markResourceViewed(row))) return
  ElMessage.success('已标记为已阅')
  if (completeRoadmapTask) {
    await completeRoadmapTaskIfMatch(row.module_id, 'code')
  }
}

async function markCodeViewedForStage(stage, task) {
  const row = findResourceForDay(stage, 'code')
  if (!row) {
    ElMessage.info('未找到对应代码案例，请刷新资源或在「优秀代码案例」列表中标记')
    return
  }
  await markCodeViewed(row, { completeRoadmapTask: true })
}

async function toggleTask(stage, task, completed) {
  const stageNo = stage.stage || stage.day
  const wasComplete = stage.stage_completed || stage.day_completed
  try {
    roadmapProgress.value = await updateRoadmapTask({
      student_id: studentId,
      stage: stageNo,
      day: stageNo,
      task_id: task.id,
      completed
    })
    if (completed) {
      ElMessage.success('任务已完成，已解锁下一项')
      const nowStage = currentStage.value
      const nowComplete = nowStage?.stage_completed || nowStage?.day_completed
      if (nowComplete && !wasComplete) {
        if (roadmapProgress.value?.advanced) {
          roadmapStageCompleteHint.value =
            '本阶段任务已全部完成！已根据最新学情自动进入下一薄弱模块，请点击「更新习题」获取新一轮题目。'
          await loadPlan()
        } else {
          roadmapStageCompleteHint.value = '本阶段任务已全部完成！'
        }
        trackBehavior(studentId, 'roadmap_day_complete', {
          stage: stageNo,
          module_id: nowStage?.module_id
        })
      }
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '更新任务失败')
  }
}

function goExerciseCenter(mode) {
  const hasExercise = tabExam.value.some(
    (r) => !r.preview && !r.pending_generate && r.contentJson
  )
  if (!hasExercise) {
    ElMessage.warning('请先点击「星火 AI 深度生成」，为本批薄弱模块生成专项习题')
    return
  }
  router.push({
    path: '/learn/exercise-center',
    query: {
      studentId,
      mode,
      from: 'resource'
    }
  })
}

function goRoadmapExercise(stage) {
  const mid = stage.module_id
  const exerciseRes = sortedResources.value.find(
    (r) =>
      r.resourceType === 'exercise' &&
      !r.preview &&
      !r.pending_generate &&
      r.contentJson &&
      Number(r.module_id) === Number(mid)
  )
  if (!exerciseRes) {
    ElMessage.warning('请先一键生成学习资源，生成本模块专项习题')
    return
  }
  router.push({
    path: '/learn/exercise-center',
    query: {
      studentId,
      moduleId: mid,
      mode: 'roadmap',
      day: stage.stage || stage.day,
      from: 'resource',
      resourceId: String(exerciseRes.id)
    }
  })
}

async function loadPlan({ preserveTab = false } = {}) {
  planLoading.value = true
  generateError.value = ''
  try {
    const data = await getResourcePlan({
      student_id: studentId,
      module_id: moduleId.value,
      bundle_mode: bundleMode.value,
      trigger_type: route.query.trigger || 'profile_button'
    })
    plan.value = data
    if (!preserveTab) {
      applyDefaultTab()
    }
    await loadRoadmapProgress()
    if (route.query.trigger === 'assessment_complete') {
      ElMessage.success('已根据评估结果更新资源推荐与路径排序')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || e?.message || '加载计划失败')
  } finally {
    planLoading.value = false
  }
}

async function regenerateByTabType() {
  if (!getToken()) {
    ElMessage.warning('请先登录后再使用星火 AI 生成（需 Java 后端 8080 已启动）')
    return
  }
  if (!plan.value?.generate_request) {
    ElMessage.warning('请等待学情计划加载完成')
    return
  }
  const agentTypes = TAB_AGENT_TYPES[activeTab.value] || ['EXERCISE']
  const typeLabel = tabTypeLabel.value
  regenerating.value = true
  generateError.value = ''
  trackBehavior(studentId, 'resource_regenerate', {
    source: 'personalized_page',
    tab: activeTab.value,
    agentTypes
  })
  try {
    const req = { ...plan.value.generate_request, agentTypes }
    const beforeCount = resources.value.length
    lastTask.value = await generateResource(req)
    await loadResources()
    await loadResourceStatus()
    newAiCount.value = Math.max(0, resources.value.length - beforeCount)
    ElNotification({
      title: '更新完成',
      message: `已为本批薄弱模块重新生成${typeLabel}`,
      type: 'success',
      duration: 5000
    })
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || '更新失败'
    if (e?.response?.status === 401) {
      generateError.value = '登录已过期或未登录，请重新登录后再生成'
    } else if (msg.includes('Network Error') || msg.includes('timeout')) {
      generateError.value =
        '无法连接 Java 后端（8080）或请求超时，请确认 Spring Boot 已启动且讯飞密钥已配置'
    } else {
      generateError.value = msg
    }
    ElMessage.error(generateError.value)
  } finally {
    regenerating.value = false
  }
}

async function runGenerate() {
  if (!getToken()) {
    generateError.value = '请先登录后再使用星火 AI 生成（需 Java 后端 8080 已启动）'
    ElMessage.warning(generateError.value)
    return
  }
  if (!plan.value?.generate_request) {
    ElMessage.warning('请等待学情计划加载完成')
    return
  }
  generating.value = true
  generateError.value = ''
  trackBehavior(studentId, 'resource_generate', { source: 'personalized_page' })
  try {
    const req = { ...plan.value.generate_request }
    const beforeCount = resources.value.length
    lastTask.value = await generateResource(req)
    await loadResources()
    newAiCount.value = Math.max(0, resources.value.length - beforeCount)
    ElNotification({
      title: 'AI 资源生成完成',
      message: `已为 ${(req.knowledgePoints || [req.knowledgePoint]).filter(Boolean).length || '各'} 薄弱模块生成讲义/案例/专项习题；再次点击将更新本批题目`,
      type: 'success',
      duration: 6000
    })
    activeTab.value = 'exam'
  } catch (e) {
    const msg = e?.response?.data?.message || e?.message || '生成失败'
    if (e?.response?.status === 401) {
      generateError.value = '登录已过期或未登录，请重新登录后再生成'
    } else if (msg.includes('Network Error') || msg.includes('timeout')) {
      generateError.value =
        '无法连接 Java 后端（8080）或请求超时，请确认 Spring Boot 已启动且讯飞密钥已配置'
    } else {
      generateError.value = msg
    }
    ElMessage.error(generateError.value)
  } finally {
    generating.value = false
  }
}

async function loadResources() {
  if (!getToken()) return
  loading.value = true
  try {
    const kps = plan.value?.knowledge_points || []
    const all = await listResources({ studentId, subject: COURSE_NAME })
    if (kps.length) {
      const filtered = all.filter(
        (r) => kps.some((kp) => r.knowledgePoint?.includes(kp) || kp.includes(r.knowledgePoint))
      )
      resources.value = filtered.length ? filtered : all
    } else {
      resources.value = all
    }
  } catch {
    /* 未登录时仍展示 preview */
  } finally {
    loading.value = false
  }
}

async function refreshAll({ preserveTab = false } = {}) {
  newAiCount.value = 0
  await loadPlan({ preserveTab })
  await loadResources()
  await loadResourceStatus()
}

function openDetail(row) {
  current.value = row
  drawerVisible.value = true
}

function copyCode(text) {
  const code = extractCodeBlock(text)
  navigator.clipboard.writeText(code).then(
    () => ElMessage.success('已复制到剪贴板'),
    () => ElMessage.error('复制失败')
  )
}

onMounted(async () => {
  if (profileCompleted.value) {
    await loadPlan()
    await loadResources()
    await loadResourceStatus()
  }
})

onActivated(async () => {
  if (profileCompleted.value && route.query.from === 'resource') {
    await refreshAll({ preserveTab: true })
  }
})

watch(profileCompleted, async (completed) => {
  if (completed) {
    await loadPlan()
    await loadResources()
    await loadResourceStatus()
  }
})
</script>

<style scoped>
.personalized-page {
  width: 100%;
  padding-bottom: 32px;
}
.flow-card {
  margin-bottom: 16px;
}
.flow-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.flow-step {
  font-size: 13px;
  color: #909399;
  cursor: pointer;
}
.flow-step--active {
  color: #303133;
  font-weight: 600;
}
.flow-arrow {
  color: #c0c4cc;
  font-size: 12px;
}
.summary-card {
  margin-bottom: 16px;
}
.summary-body {
  min-height: 80px;
}
.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.basis-card {
  margin-bottom: 14px;
}
.basis-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.basis-section {
  margin-bottom: 12px;
}
.basis-subtitle {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}
.basis-hint,
.basis-empty {
  margin: 6px 0 0;
  font-size: 12px;
  color: #909399;
}
.recommend-block {
  margin: 12px 0;
  padding: 10px 12px;
  background: #f0f9ff;
  border-radius: 8px;
  border: 1px solid #d9ecff;
}
.recommend-summary {
  margin: 0;
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
}
.summary-line {
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
  margin: 8px 0 0;
}
.push-modes {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.push-mode-item {
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #606266;
}
.push-mode-item strong {
  display: block;
  color: #303133;
  margin-bottom: 2px;
}
.action-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.task-alert {
  margin-top: 12px;
}
.stats-row {
  margin-bottom: 16px;
}
.stat-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px;
  text-align: center;
}
.stat-num {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}
.stat-label {
  font-size: 12px;
  color: #909399;
}
.stat-card--eval .stat-num {
  color: #f56c6c;
}
.stat-card--profile .stat-num {
  color: #e6a23c;
}
.stat-card--ai .stat-num {
  color: #409eff;
}
.tab-body {
  min-height: 120px;
}
.tab-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}
.extra-body {
  color: #303133;
}
.roadmap-hint {
  margin-bottom: 12px;
}
.roadmap-progress-bar {
  margin-bottom: 12px;
  font-size: 13px;
  color: #606266;
}
.progress-line {
  margin-top: 6px;
}
.day-complete-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #67c23a;
}
.stage-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}
.done-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.done-step {
  font-size: 12px;
  color: #67c23a;
  background: #f0f9eb;
  padding: 4px 10px;
  border-radius: 4px;
}
.task-current {
  padding: 16px;
  border: 1px solid #dcdfe6;
  border-radius: 10px;
  background: #fff;
}
.task-current-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.task-current-label {
  font-size: 12px;
  font-weight: 600;
  color: #e6a23c;
}
.task-current-title {
  margin: 0 0 12px;
  font-size: 15px;
  color: #303133;
  line-height: 1.5;
}
.task-current-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.history-block {
  margin-top: 16px;
}
.history-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
  color: #606266;
}
.roadmap-day {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafafa;
}
.roadmap-day--locked {
  opacity: 0.65;
  background: #f5f7fa;
}
.roadmap-day--done {
  border-color: #b3e19d;
  background: #f0f9eb;
}
.day-head h4 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.task-list {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
}
.task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
  flex-wrap: wrap;
}
.task-item:last-child {
  border-bottom: none;
}
.task-title {
  margin-right: 6px;
}
.locked-hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: #909399;
}
.block-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.tips-block,
.links-block {
  margin-top: 16px;
}
.tips-list,
.link-list {
  padding-left: 1.2em;
  line-height: 1.7;
  margin: 0;
  color: #606266;
}
.link-list a {
  color: #409eff;
}
.practice-link {
  margin-top: 12px;
}
@media (max-width: 900px) {
  .push-modes {
    grid-template-columns: 1fr;
  }
}
</style>
