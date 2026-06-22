<template>
  <div class="profile-page">
    <el-alert
      v-if="isDemoMode"
      title="演示模式 · 以下为示例学生学习画像（只读）"
      type="info"
      :closable="false"
      show-icon
      class="demo-banner"
    />

    <!-- 用户画像 -->
    <el-card v-if="!isDemoMode && !isAdmin" shadow="never" class="flow-card">
      <div class="flow-steps">
        <span class="flow-step flow-step--active">① 用户画像</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step" @click="$router.push('/evaluation')">② 学习效果评估</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step" @click="$router.push('/resource/personalized')">③ 学习资源</span>
      </div>
      <p class="flow-hint">本页展示学习画像快照，由对话构建、练习测试、智能辅导等行为实时更新。</p>
    </el-card>

    <section class="profile-hero">
      <div class="hero-card">
        <div class="hero-avatar" :class="{ 'has-image': !!avatarUrl }">
          <img v-if="avatarUrl" :src="avatarUrl" alt="" class="hero-avatar-img" />
          <span v-else class="hero-avatar-initial">{{ heroInitial }}</span>
        </div>
        <div class="hero-body">
          <h1 class="hero-title">{{ displayBasic.realName || '学习者' }}</h1>
          <p class="hero-desc">Python 课程学习画像 · 掌握度与成长轨迹</p>
          <div v-if="!isAdmin && !isDemoMode" class="hero-actions">
            <el-button size="small" @click="$router.push('/settings')">编辑资料</el-button>
            <el-button size="small" @click="$router.push('/profile/dialogue')">构建 / 更新画像</el-button>
            <el-button size="small" type="primary" @click="$router.push('/evaluation')">学习效果评估</el-button>
          </div>
        </div>
        <div v-if="masteryData.has_profile" class="hero-badge">
          <span class="hero-badge-label">综合评级</span>
          <span class="hero-badge-value" :class="`rating-${overallRating.level}`">
            {{ overallRating.label }}
          </span>
        </div>
      </div>
    </section>

    <!-- 区域 1：基础信息栏 -->
    <section v-loading="loading" class="profile-section">
      <div class="section-card">
        <div class="section-header">
          <h2 class="section-title">基础信息</h2>
          <el-tag v-if="isAdmin" type="warning" size="small">管理员视图</el-tag>
        </div>

        <el-alert
          v-if="!hasBasicInfo && !isAdmin"
          title="尚未填写基础信息，请前往「设置」进行填写。"
          type="warning"
          :closable="false"
          show-icon
          class="section-alert"
        />

        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ displayBasic.realName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="年级">{{ displayBasic.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="专业">{{ displayBasic.major || '-' }}</el-descriptions-item>
          <el-descriptions-item label="学习偏好">
            {{ formatLearnPreferences(displayBasic.learnPreferences) || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </section>

    <template v-if="masteryData.has_profile">
      <!-- 区域 2：综合可视化区 -->
      <section v-loading="masteryLoading" class="profile-section">
        <div class="section-card">
          <div class="section-header">
            <h2 class="section-title">综合概览</h2>
            <div v-if="!isDemoMode" class="head-actions">
              <el-button type="primary" @click="goPersonalizedResources()">个性化学习资源</el-button>
              <el-button type="primary" link @click="$router.push('/evaluation')">学习效果评估</el-button>
              <el-button type="primary" link @click="$router.push('/profile/dialogue')">继续构建画像</el-button>
              <el-button type="warning" link @click="goRebuild">重新构建画像</el-button>
            </div>
          </div>

          <div class="overview-layout">
            <div class="stat-cards">
              <div class="stat-card">
                <span class="stat-label">整体平均分</span>
                <span class="stat-value" :class="scoreClass(overallRating.avg)">
                  {{ overallRating.avg ?? '-' }}
                </span>
                <span class="stat-unit">分</span>
              </div>
              <div class="stat-card">
                <span class="stat-label">综合评级</span>
                <span class="stat-value rating" :class="`rating-${overallRating.level}`">
                  {{ overallRating.label }}
                </span>
              </div>
            </div>
            <div class="charts-row">
              <div class="chart-block">
                <p class="chart-caption">{{ isDemoMode ? 'TOP3 薄弱模块' : 'TOP3 薄弱模块 · 点击进入练习' }}</p>
                <WeakModulesBarChart
                  :modules="topWeakModules"
                  order="asc"
                  height="200px"
                  @module-click="onModulePracticeClick"
                />
              </div>
              <div class="chart-block">
                <p class="chart-caption">{{ isDemoMode ? 'TOP3 优势模块' : 'TOP3 优势模块 · 点击进入练习' }}</p>
                <WeakModulesBarChart
                  :modules="topStrongModules"
                  order="desc"
                  height="200px"
                  @module-click="onModulePracticeClick"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 区域 3：模块掌握雷达图 -->
      <section v-loading="masteryLoading" class="profile-section">
        <div class="section-card">
          <div class="section-header">
            <h2 class="section-title">模块掌握雷达图</h2>
            <span class="section-sub">{{ isDemoMode ? '由画像构建对话、练习与交流自动评估' : '由画像构建对话、练习与交流自动评估 · 点击模块进入练习' }}</span>
          </div>
          <div class="chart-block chart-full">
            <MasteryRadarChart
              :modules="masteryData.modules"
              height="420px"
              mode="score"
              @module-click="onModulePracticeClick"
            />
          </div>
        </div>
      </section>

      <!-- 区域 4：学习趋势折线图 -->
      <section v-if="showTrendChart" v-loading="masteryLoading" class="profile-section">
        <div class="section-card">
          <div class="section-header">
            <h2 class="section-title">学习趋势</h2>
            <span class="section-sub">历次测评平均分变化</span>
          </div>
          <div class="chart-block chart-full">
            <TrendLineChart :points="trendPoints" height="300px" />
          </div>
        </div>
      </section>

      <!-- 区域 5：学习成长时间轴 -->
      <section v-loading="masteryLoading" class="profile-section">
        <div class="section-card">
          <div class="section-header">
            <div class="section-header-left">
              <h2 class="section-title">学习成长时间轴</h2>
              <span v-if="timelineEvents.length" class="section-sub">
                共 {{ timelineEvents.length }} 条记录
              </span>
            </div>
            <el-button
              v-if="timelineEvents.length"
              link
              type="primary"
              @click="timelineExpanded = !timelineExpanded"
            >
              {{ timelineExpanded ? '收起' : '展开' }}
            </el-button>
          </div>
          <el-empty v-if="!timelineEvents.length" description="暂无成长记录" />
          <template v-else>
            <div v-if="!timelineExpanded" class="timeline-collapsed-preview">
              <span class="timeline-collapsed-label">最近</span>
              <time class="timeline-time">{{ timelineEvents[0].datetimeLabel }}</time>
              <span class="timeline-title">{{ timelineEvents[0].title }}</span>
              <p class="timeline-desc">{{ timelineEvents[0].description }}</p>
            </div>
            <el-collapse-transition>
              <ul v-show="timelineExpanded" class="growth-timeline">
                <li v-for="(evt, idx) in timelineEvents" :key="idx" class="timeline-item">
                  <div class="timeline-dot" />
                  <div class="timeline-body">
                    <time class="timeline-time">{{ evt.datetimeLabel }}</time>
                    <span class="timeline-title">{{ evt.title }}</span>
                    <p class="timeline-desc">{{ evt.description }}</p>
                  </div>
                </li>
              </ul>
            </el-collapse-transition>
          </template>
        </div>
      </section>

      <!-- 区域 6：学情标签区 -->
      <section v-loading="masteryLoading || tagNavLoading" class="profile-section">
        <div class="section-card">
          <div class="section-header">
            <h2 class="section-title">学情标签</h2>
            <span class="section-sub">{{ isDemoMode ? '薄弱点、已掌握与待加强标签' : '点击标签进入模块练习' }}</span>
          </div>
          <div class="tag-columns">
            <div v-for="group in tagGroups" :key="group.key" class="tag-column">
              <h3 class="tag-column-title">{{ group.title }}</h3>
              <div v-if="group.items.length" class="tag-chip-list">
                <button
                  v-for="(item, i) in group.items"
                  :key="`${group.key}-${i}`"
                  type="button"
                  class="tag-chip"
                  :class="{ 'tag-chip--disabled': !item.navigable || isDemoMode }"
                  :disabled="tagNavLoading || !item.navigable || isDemoMode"
                  @click="onTagClick(item)"
                >
                  {{ item.label }}
                </button>
              </div>
              <p v-else class="tag-empty">暂无</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 区域 7：AI 智能解读区 -->
      <section v-loading="masteryLoading" class="profile-section">
        <div class="section-card ai-section">
          <div class="section-header">
            <h2 class="section-title">AI 智能解读</h2>
          </div>
          <div class="ai-block">
            <h3 class="ai-subtitle">学习总结</h3>
            <p class="ai-text">{{ aiSummary }}</p>
          </div>
          <div class="ai-block">
            <h3 class="ai-subtitle">个性化练习建议</h3>
            <ul class="ai-suggest-list">
              <li v-for="(s, i) in practiceSuggestions" :key="i">{{ s }}</li>
            </ul>
          </div>
        </div>
      </section>
    </template>

    <!-- 无画像数据 -->
    <section v-else v-loading="masteryLoading" class="profile-section">
      <div class="section-card">
        <el-empty :description="isDemoMode ? '暂无掌握数据' : '暂无掌握数据，请先完成画像构建'">
          <el-button v-if="!isDemoMode" type="primary" @click="$router.push('/profile/dialogue')">开始构建</el-button>
        </el-empty>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getProfile } from '../api/profile'
import { getPublicDemoProfile, PUBLIC_DEMO_STUDENT_ID } from '../api/publicDemo'
import {
  getStudentId,
  getStoredUser,
  getMe,
  getStudent
} from '../api/auth'
import { getModuleMastery, navigateByTag } from '../api/profileBuild'
import MasteryRadarChart from '../components/MasteryRadarChart.vue'
import WeakModulesBarChart from '../components/WeakModulesBarChart.vue'
import TrendLineChart from '../components/TrendLineChart.vue'
import {
  computeOverallRating,
  getTopWeakModules,
  getTopStrongModules,
  buildTrendPoints,
  aggregateTagGroups,
  buildPracticeSuggestions,
  buildTimelineEvents
} from '../utils/profileDashboard'
import {
  formatLearnPreferences,
  parseLearnPreferences
} from '../constants/profileBasic'
import { useAvatarUrl, getDisplayInitial } from '../utils/avatarStorage'

const router = useRouter()
const route = useRoute()
const currentUser = getStoredUser()
const isDemoMode = computed(() => !!route.meta.demo)
const isAdmin = computed(() => !isDemoMode.value && currentUser?.role === 'admin')

const studentId = computed(() => {
  if (isDemoMode.value) return PUBLIC_DEMO_STUDENT_ID
  const q = route.query.studentId
  if (q) return Number(q)
  return getStudentId()
})

const avatarUrl = useAvatarUrl(studentId)

const profile = ref(null)
const loading = ref(false)
const masteryLoading = ref(false)
const masteryData = ref({
  has_profile: false,
  modules: [],
  summary: {},
  ai_interpretation: '',
  snapshots: [],
  change_logs: []
})
const tagNavLoading = ref(false)
const timelineExpanded = ref(false)

const displayBasic = reactive({
  realName: '',
  grade: '',
  major: '',
  learnPreferences: ''
})

const heroInitial = computed(() =>
  getDisplayInitial({ realName: displayBasic.realName, username: currentUser?.username })
)

const overallRating = computed(() => {
  const avg = masteryData.value.summary?.avg_score
  const rating = computeOverallRating(avg)
  return { avg, ...rating }
})

const topWeakModules = computed(() => getTopWeakModules(masteryData.value.modules, 3))

const topStrongModules = computed(() => getTopStrongModules(masteryData.value.modules, 3))

const trendPoints = computed(() => buildTrendPoints(masteryData.value.snapshots))

const showTrendChart = computed(() => trendPoints.value.length >= 2)

const timelineEvents = computed(() =>
  buildTimelineEvents(masteryData.value.snapshots, masteryData.value.change_logs)
)

const tagGroups = computed(() => aggregateTagGroups(masteryData.value.modules))

const aiSummary = computed(
  () =>
    masteryData.value.ai_interpretation ||
    '请先完成学习测评，系统将自动生成专属学习总结。'
)

const practiceSuggestions = computed(() =>
  buildPracticeSuggestions(masteryData.value.modules, masteryData.value.summary)
)

const hasBasicInfo = computed(
  () =>
    !!(
      displayBasic.realName ||
      displayBasic.grade ||
      displayBasic.major ||
      parseLearnPreferences(displayBasic.learnPreferences).length
    )
)

function goModulePractice(moduleId, source = 'chart') {
  if (!studentId.value) {
    ElMessage.warning('请先登录')
    return
  }
  if (moduleId == null) return
  router.push({
    path: '/learn/exercise-center',
    query: {
      studentId: studentId.value,
      moduleId,
      mode: 'module',
      source
    }
  })
}

function onModulePracticeClick(mod) {
  if (isDemoMode.value) return
  if (!mod?.module_id) return
  goModulePractice(mod.module_id, 'chart')
}

function goPersonalizedResources(moduleId = null) {
  if (!studentId.value) {
    ElMessage.warning('请先登录')
    return
  }
  const query = { bundleMode: 'single', trigger: 'profile_button' }
  if (moduleId != null) query.moduleId = moduleId
  router.push({ path: '/resource/personalized', query })
}

async function onTagClick(item) {
  if (!item.navigable || !studentId.value) {
    ElMessage.warning('该标签暂无关联模块，请先完成模块测评')
    return
  }
  tagNavLoading.value = true
  try {
    const data = await navigateByTag({
      student_id: studentId.value,
      tag_type: item.tagType,
      tag_content: item.tagContent,
      module_id: item.moduleId
    })
    if (data.route_path) {
      router.push(data.route_path)
    } else {
      ElMessage.warning('未获取到跳转地址')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || e?.message || '跳转失败')
  } finally {
    tagNavLoading.value = false
  }
}

function scoreClass(score) {
  if (score == null) return ''
  if (score >= 85) return 'score-high'
  if (score >= 45) return 'score-mid'
  return 'score-low'
}

function fillBasicFromUser(u) {
  if (!u) return
  displayBasic.realName = u.realName || ''
  displayBasic.grade = u.grade || ''
  displayBasic.major = u.major || ''
  displayBasic.learnPreferences = u.learnPreferences || u.learnPreference || ''
}

function fillBasicFromStorage() {
  fillBasicFromUser(getStoredUser())
}

function mergeBasicFromProfile(p) {
  if (!p) return
  if (!displayBasic.realName && p.realName) displayBasic.realName = p.realName
  if (!displayBasic.grade && p.grade) displayBasic.grade = p.grade
  if (!displayBasic.major && p.major) displayBasic.major = p.major
  if (!displayBasic.learnPreferences && (p.learnPreferences || p.learnPreference)) {
    displayBasic.learnPreferences = p.learnPreferences || p.learnPreference
  }
}

async function loadBasicInfo() {
  fillBasicFromStorage()
  if (!studentId.value) return
  try {
    const viewingOther = isAdmin.value && studentId.value !== getStudentId()
    const data = viewingOther
      ? await getStudent(studentId.value)
      : await getMe()
    fillBasicFromUser(data)
  } catch {
    /* 保留 localStorage 回退 */
  }
}

async function loadMastery() {
  if (!studentId.value) return
  masteryLoading.value = true
  try {
    masteryData.value = await getModuleMastery(studentId.value)
  } catch {
    /* 拦截器已提示 */
  } finally {
    masteryLoading.value = false
  }
}

async function load() {
  loading.value = true
  try {
    if (isDemoMode.value) {
      profile.value = await getPublicDemoProfile(PUBLIC_DEMO_STUDENT_ID)
      fillBasicFromUser(profile.value)
      mergeBasicFromProfile(profile.value)
      return
    }
    await loadBasicInfo()
    if (!studentId.value) return
    profile.value = await getProfile(studentId.value)
    mergeBasicFromProfile(profile.value)
  } catch {
    profile.value = null
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  await Promise.all([loadMastery(), load()])
}

async function goRebuild() {
  try {
    await ElMessageBox.confirm(
      '将清空测评分数与标签（保留个人设置中的基础信息），并从头重新构建。是否继续？',
      '重新构建画像',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  router.push({ path: '/profile/dialogue', query: { rebuild: '1' } })
}

onMounted(refreshAll)
onActivated(refreshAll)
</script>

<style scoped>
.profile-page {
  padding: 0 0 32px;
  position: relative;
}

.demo-banner {
  margin-bottom: 16px;
}

.flow-card {
  margin-bottom: 16px;
}
.flow-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
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
.flow-hint {
  margin: 0;
  font-size: 13px;
  color: #606266;
}

.profile-hero {
  margin-bottom: 20px;
}

.hero-card {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding: 24px 28px;
  background: var(--tp-card, #fff);
  border: 1px solid var(--tp-border, #eeeef2);
  border-radius: var(--tp-radius-card, 16px);
  box-shadow: var(--tp-shadow, 0 2px 16px rgba(180, 190, 205, 0.1));
}

.hero-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--tp-hover, #f4f5f8);
  border: 1px solid var(--tp-border, #eeeef2);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-avatar.has-image {
  background: #fff;
}

.hero-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-avatar-initial {
  font-size: 22px;
  font-weight: 600;
  color: var(--tp-text, #333338);
}

.hero-body {
  flex: 1;
  min-width: 180px;
}

.hero-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--tp-text, #333338);
}

.hero-desc {
  margin: 6px 0 12px;
  font-size: 13px;
  color: var(--tp-muted, #757582);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-badge {
  flex-shrink: 0;
  text-align: center;
  padding: 12px 20px;
  background: var(--tp-bg, #f7f8fa);
  border-radius: var(--tp-radius-btn, 12px);
  border: 1px solid var(--tp-border, #eeeef2);
}

.hero-badge-label {
  display: block;
  font-size: 12px;
  color: var(--tp-muted, #757582);
  margin-bottom: 4px;
}

.hero-badge-value {
  font-size: 18px;
  font-weight: 600;
}

.profile-section + .profile-section {
  margin-top: 20px;
}

.section-card {
  background: var(--tp-card, #fff);
  border: 1px solid var(--tp-border, #eeeef2);
  border-radius: var(--tp-radius-card, 16px);
  padding: 22px 26px;
  box-shadow: var(--tp-shadow, 0 2px 12px rgba(180, 190, 205, 0.08));
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--tp-border, #eeeef2);
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--tp-text, #333338);
}

.section-sub {
  font-size: 13px;
  color: var(--tp-muted, #757582);
}

.section-alert {
  margin-bottom: 16px;
}

.head-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* 区域 2：综合可视化 */
.overview-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 24px;
  align-items: stretch;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  min-width: 0;
}

.stat-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 20px 16px;
  background: var(--tp-bg, #f7f8fa);
  border-radius: var(--tp-radius-btn, 12px);
  border: 1px solid var(--tp-border, #eeeef2);
  min-height: 88px;
}

.stat-label {
  font-size: 13px;
  color: var(--tp-muted, #757582);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.1;
}

.stat-unit {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.rating-excellent { color: #333338; }
.rating-good { color: #4a6a70; }
.rating-fair { color: #757582; }
.rating-weak { color: #9a6b6b; }
.rating-none { color: #c0c0cc; font-size: 28px; }

.score-high { color: #333338; }
.score-mid { color: #757582; }
.score-low { color: #9a6b6b; }

.chart-block {
  min-width: 0;
}

.chart-full {
  width: 100%;
}

.chart-caption {
  margin: 0 0 8px;
  font-size: 13px;
  color: #606266;
}

.section-header-left {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

/* 区域 5：时间轴 */
.timeline-collapsed-preview {
  padding: 12px 14px;
  background: #f8fafb;
  border: 1px solid var(--tp-border, #eeeef2);
  border-radius: 10px;
}

.timeline-collapsed-label {
  display: inline-block;
  margin-right: 8px;
  font-size: 12px;
  color: var(--tp-muted, #757582);
}

.timeline-collapsed-preview .timeline-title {
  display: block;
  margin-top: 4px;
}

.timeline-collapsed-preview .timeline-desc {
  margin: 6px 0 0;
}

.growth-timeline {
  list-style: none;
  margin: 0;
  padding: 0;
}

.timeline-item {
  display: flex;
  gap: 16px;
  padding-bottom: 20px;
  position: relative;
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: 0;
  width: 2px;
  background: #e4e7ed;
}

.timeline-dot {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  margin-top: 4px;
  border-radius: 50%;
  background: var(--tp-tab-active-alt, #bde8eb);
  border: 2px solid var(--tp-tab-active, #c7edf0);
}

.timeline-body {
  flex: 1;
  min-width: 0;
}

.timeline-time {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.timeline-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.timeline-desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

/* 区域 6：标签分栏 */
.tag-columns {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.tag-column {
  padding: 12px 14px;
  background: var(--tp-bg, #f7f8fa);
  border-radius: var(--tp-radius-btn, 10px);
  border: 1px solid var(--tp-border, #eeeef2);
  min-height: 80px;
}

.tag-column-title {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.tag-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip {
  margin: 0;
  padding: 6px 12px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--tp-text, #333338);
  background: var(--tp-card, #fff);
  border: 1px solid var(--tp-border, #eeeef2);
  border-radius: var(--tp-radius-tag, 8px);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  text-align: left;
}

.tag-chip:hover:not(:disabled) {
  background: var(--tp-tab-active, #c7edf0);
  border-color: var(--tp-tab-active-alt, #bde8eb);
}

.tag-chip:active:not(:disabled) {
  background: var(--tp-tab-active-alt, #bde8eb);
}

.tag-chip--disabled,
.tag-chip:disabled {
  color: #909399;
  background: #f4f4f5;
  border-color: #e4e7ed;
  cursor: not-allowed;
  box-shadow: none;
}

.tag-empty {
  margin: 0;
  font-size: 13px;
  color: #c0c4cc;
}

/* 区域 7：AI 解读 */
.ai-section .ai-block + .ai-block {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #ebeef5;
}

.ai-subtitle {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--tp-text, #333338);
}

.ai-text {
  margin: 0;
  font-size: 14px;
  color: #303133;
  line-height: 1.8;
}

.ai-suggest-list {
  margin: 0;
  padding-left: 18px;
}

.ai-suggest-list li {
  font-size: 14px;
  color: #606266;
  line-height: 1.8;
  margin-bottom: 4px;
}

@media (max-width: 768px) {
  .overview-layout {
    grid-template-columns: 1fr;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .stat-cards {
    flex-direction: row;
  }

  .stat-card {
    flex: 1;
  }

  .tag-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .tag-columns {
    grid-template-columns: 1fr;
  }

  .stat-cards {
    flex-direction: column;
  }
}
</style>
