<template>
  <div class="evaluation-page">
    <ProfileRequiredAlert :loading="profileLoading" :profile-completed="profileCompleted" />

    <el-card v-if="profileCompleted" shadow="never" class="flow-card">
      <div class="flow-steps">
        <span class="flow-step" @click="$router.push('/profile/view')">① 用户画像</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step flow-step--active">② 学习效果评估</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step" @click="$router.push('/resource/personalized')">③ 学习资源</span>
      </div>
      <p class="flow-desc">
        <strong>本页为周期性学习诊断报告</strong>：聚合近一期全部学习行为，进行跨周期对比、错题归因与方案调控。实时掌握度与学情标签请查看
        <el-button link type="primary" @click="$router.push('/profile/view')">用户画像</el-button>
      </p>
    </el-card>

    <EvalHistoryCompareBar
      v-if="compareReports.length === 2"
      :report-a="compareReports[0]"
      :report-b="compareReports[1]"
      :label-a="`RPT-${compareReports[0].id}`"
      :label-b="`RPT-${compareReports[1].id}`"
      @close="clearCompare"
    />

    <el-row v-if="profileCompleted" :gutter="16">
      <el-col :span="15">
        <el-card shadow="never" v-loading="generating">
          <template #header>
            <div class="card-head">
              <span>学习效果评估</span>
              <div class="head-actions">
                <el-tooltip placement="top" :show-after="300">
                  <template #content>
                    开启后，报告生成成功将自动打开「评估调整预览」；确认应用后将反向校准画像偏差、触发多智能体生成补强资源，并调整后续学习路径优先级。
                  </template>
                  <el-checkbox v-model="autoApply">生成后自动应用调整</el-checkbox>
                </el-tooltip>
                <el-button type="primary" :loading="generating" @click="onGenerateConfirm">
                  生成评估报告
                </el-button>
              </div>
            </div>
          </template>

          <el-empty
            v-if="!currentReport"
            description="点击「生成评估报告」进行多维度学习效果分析"
          />

          <template v-else>
            <div class="report-meta">
              <el-tag type="info" effect="plain">报告编号 {{ reportNo }}</el-tag>
              <el-tag effect="plain">生成时间 {{ formatTime(currentReport.created_at) }}</el-tag>
              <el-tag
                v-if="scoreDelta != null"
                :type="scoreDelta >= 0 ? 'success' : 'warning'"
                effect="plain"
              >
                较上次 {{ formatDelta(scoreDelta) }} 分
              </el-tag>
            </div>

            <div class="score-banner">
              <div class="score-circle">
                <span class="score-num">{{ currentReport.overall_score }}</span>
                <span class="score-label">综合得分</span>
              </div>
              <div class="score-summary">
                <p>{{ currentReport.report?.summary || currentReport.report_summary }}</p>
              </div>
            </div>

            <p class="metric-hint">以下三项均为本期相对上期的周期对比指标，与画像页实时模块分不同。</p>
            <el-row :gutter="12" class="metric-row">
              <el-col :span="8">
                <div class="metric-card">
                  <span class="metric-label">
                    较上次变化
                    <el-tooltip content="本期综合得分相对上一份评估报告的增减（分）" placement="top">
                      <el-icon class="metric-tip"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </span>
                  <span class="metric-value" :class="deltaClass">
                    {{ scoreDelta != null ? formatDelta(scoreDelta) : '—' }}
                  </span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric-card">
                  <span class="metric-label">
                    测评提升
                    <el-tooltip
                      content="本评估周期内画像快照平均分的变化（非实时单点）"
                      placement="top"
                    >
                      <el-icon class="metric-tip"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </span>
                  <span class="metric-value">
                    {{ formatDelta(displayMetrics.snapshot_trend?.improvement_pct) }} 分
                  </span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric-card">
                  <span class="metric-label">
                    学习活跃度
                    <el-tooltip
                      content="本周期内学习行为综合活跃度（答题、资源、辅导等）"
                      placement="top"
                    >
                      <el-icon class="metric-tip"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </span>
                  <span class="metric-value">{{ displayMetrics.behavior?.activity_score ?? 0 }}</span>
                </div>
              </el-col>
            </el-row>

            <div v-if="stageBalance.length" class="stage-block">
              <h4 class="section-title">分阶段掌握平衡图</h4>
              <p class="stage-hint">
                课程划分为四个学习阶段；点击阶段柱可查看本期 vs 上期进退步对比。
              </p>
              <StageBalanceChart :stages="stageBalance" @stage-click="openStageDialog" />
              <div class="stage-legend">
                <span class="legend-item"><i class="legend-dot legend-dot--blue" />蓝色柱：本周期阶段平均分</span>
                <span class="legend-item"><i class="legend-dot legend-dot--red" />红色柱：本周期最需加强阶段</span>
                <span class="legend-item"><i class="legend-dot legend-dot--gray" />灰色虚线：四阶段均衡参考线</span>
              </div>
            </div>

            <div class="trend-block">
              <div class="trend-head">
                <h4 class="section-title">历次评估总分成长趋势</h4>
                <el-select v-model="trendFilter" size="small" class="trend-select" @change="renderTrendChart">
                  <el-option
                    v-for="opt in trendFilterOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </div>
              <p v-if="trendPointCount < 2" class="trend-single-hint">
                当前仅有 {{ trendPointCount }} 次评估记录。完成更多期评估后，此处将展示纵向成长曲线——这是评估页独有的跨周期视角（画像页展示的是快照趋势）。
              </p>
              <div ref="trendChartRef" class="trend-chart" />
            </div>

            <WrongAnalysisPanel
              :student-id="studentId"
              :period-start="evalPeriodStart"
              :period-end="evalPeriodEnd"
            />

            <el-divider />

            <el-row :gutter="16">
              <el-col :span="12">
                <h4 class="section-title">本期优势与进步根源</h4>
                <ul class="text-list">
                  <li v-for="(s, i) in currentReport.report?.strengths || []" :key="i">{{ s }}</li>
                </ul>
              </el-col>
              <el-col :span="12">
                <h4 class="section-title">本期待改进与问题成因</h4>
                <ul class="text-list">
                  <li v-for="(w, i) in currentReport.report?.weaknesses || []" :key="i">{{ w }}</li>
                </ul>
              </el-col>
            </el-row>

            <h4 class="section-title">周期性学习方案建议</h4>
            <p class="suggest-hint">
              以下建议基于本周期诊断，应用评估调整后将同步写入学习路径与资源推送。
            </p>
            <ul class="recommend-list">
              <li v-for="(r, i) in currentReport.report?.recommendations || []" :key="i" class="recommend-item">
                <span>{{ r }}</span>
                <el-button
                  v-if="recommendModule(r)"
                  link
                  type="primary"
                  size="small"
                  @click="goPractice(recommendModule(r))"
                >
                  去练习
                </el-button>
              </li>
            </ul>

            <div v-if="applyLog" class="apply-log-wrap">
              <el-alert
                :title="`已于 ${formatTime(applyLog.applied_at)} 应用评估调整`"
                :description="applyLog.summary"
                type="success"
                :closable="false"
                show-icon
                class="apply-log-alert"
              />
              <el-button link type="primary" size="small" @click="applyDetailVisible = true">
                查看详情
              </el-button>
            </div>

            <div class="apply-actions">
              <el-button type="primary" :loading="applying" @click="openPreview">
                应用评估调整（优化推送与学习计划）
              </el-button>
              <el-button @click="goPersonalizedResources">查看学习资源</el-button>
              <el-button link type="primary" @click="$router.push('/profile/view')">
                查看用户画像 →
              </el-button>
            </div>
          </template>
        </el-card>
      </el-col>

      <el-col :span="9">
        <el-card shadow="never" v-loading="historyLoading">
          <template #header>
            <div class="history-head">
              <span>历史评估</span>
              <el-button
                link
                :type="compareMode ? 'primary' : 'default'"
                size="small"
                @click="toggleCompareMode"
              >
                {{ compareMode ? '取消对比' : '对比模式' }}
              </el-button>
            </div>
          </template>

          <p v-if="compareMode" class="compare-mode-hint">勾选两份报告后自动展示顶部对比条（最多 2 份）</p>

          <el-empty v-if="!history.length" description="暂无历史评估报告">
            <template #description>
              <p class="empty-desc-title">暂无历史评估报告</p>
              <p class="empty-desc-sub">
                点击左侧「生成评估报告」创建首期诊断；之后每次生成将自动与上期对比，形成成长轨迹。
              </p>
            </template>
          </el-empty>

          <el-tooltip
            v-for="item in history"
            :key="item.id"
            placement="left"
            :show-after="400"
            :disabled="compareMode"
          >
            <template #content>
              <div class="history-tooltip">
                <p>RPT-{{ item.id }} · {{ formatTime(item.created_at) }}</p>
                <p v-if="item.score_delta != null">较上次 {{ formatDelta(item.score_delta) }} 分</p>
                <p>{{ item.report_summary }}</p>
              </div>
            </template>
            <div
              class="history-item"
              :class="{ 'history-item--active': currentReport?.id === item.id }"
              @click="onHistoryClick(item)"
            >
              <el-checkbox
                v-if="compareMode"
                class="history-check"
                :model-value="compareSelected.includes(item.id)"
                @change="(v) => toggleCompareSelect(item.id, v)"
                @click.stop
              />
              <div class="history-score">{{ item.overall_score }}</div>
              <div class="history-body">
                <p class="history-tag">RPT-{{ item.id }}</p>
                <p class="history-summary">{{ item.report_summary }}</p>
                <time class="history-time">{{ formatTime(item.created_at) }}</time>
              </div>
            </div>
          </el-tooltip>
        </el-card>
      </el-col>
    </el-row>

    <!-- 阶段进退步对比 -->
    <el-dialog v-model="stageDialogVisible" title="阶段进退步对比" width="420px" destroy-on-close>
      <div v-if="stageDialogData" class="stage-dialog">
        <h4>{{ stageDialogData.current.stage_name }}</h4>
        <div class="stage-compare-row">
          <div class="stage-compare-cell">
            <span class="cell-label">本期得分</span>
            <span class="cell-value">{{ stageDialogData.current.avg_score }} 分</span>
          </div>
          <div class="stage-compare-cell">
            <span class="cell-label">上期得分</span>
            <span class="cell-value">{{ stageDialogData.prevScore ?? '—' }} 分</span>
          </div>
          <div class="stage-compare-cell">
            <span class="cell-label">变化</span>
            <span class="cell-value" :class="stageDeltaClass">
              {{ stageDialogData.delta != null ? `${formatDelta(stageDialogData.delta)} 分` : '—' }}
              <span v-if="stageDialogData.delta > 0">↑</span>
              <span v-else-if="stageDialogData.delta < 0">↓</span>
            </span>
          </div>
        </div>
        <p v-if="stageDialogAttribution" class="stage-attribution">{{ stageDialogAttribution }}</p>
      </div>
    </el-dialog>

    <!-- 评估调整预览 -->
    <el-dialog v-model="previewVisible" title="评估调整预览" width="520px" destroy-on-close>
      <div v-if="preview" class="preview-body">
        <p class="preview-intro">
          确认后将根据评估结果动态调整资源推送策略与学习计划（提升薄弱项优先级并刷新推送）：
        </p>
        <h5>路径优先级</h5>
        <ul class="preview-list">
          <li v-for="(c, i) in preview.priority_changes" :key="i">
            <strong>{{ c.module_name }}</strong>：{{ c.from_priority }} → {{ c.to_priority }}
          </li>
        </ul>
        <h5>资源推送策略</h5>
        <p class="preview-text">{{ preview.push_strategy }}</p>
        <p class="preview-text">
          优先推送：
          <el-tag v-for="t in preview.prefer_resource_labels" :key="t" size="small" class="tag-gap">
            {{ t }}
          </el-tag>
          （预计约 {{ preview.estimated_push_count }} 条）
        </p>
        <h5>学习计划调整</h5>
        <ul class="preview-list">
          <li v-for="(n, i) in preview.roadmap_notes" :key="i">{{ n }}</li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">取消</el-button>
        <el-button type="primary" :loading="applying" @click="confirmApply">确认应用</el-button>
      </template>
    </el-dialog>

    <!-- 已应用调整详情 -->
    <el-dialog v-model="applyDetailVisible" title="本次调整明细" width="520px" destroy-on-close>
      <div v-if="applyLog" class="preview-body">
        <h5>画像校准</h5>
        <ul class="preview-list">
          <li v-for="(m, i) in applyLog.weak_modules || []" :key="i">
            提升薄弱模块优先级：{{ m }}
          </li>
          <li v-if="!applyLog.weak_modules?.length">维持当前模块优先级</li>
        </ul>
        <h5>智能体资源生成</h5>
        <p class="preview-text">{{ applyLog.push_strategy || '—' }}</p>
        <p class="preview-text">
          优先资源类型：
          <el-tag
            v-for="t in applyLog.prefer_resource_types || []"
            :key="t"
            size="small"
            class="tag-gap"
          >
            {{ resourceTypeLabel(t) }}
          </el-tag>
        </p>
        <h5>学习路径调整</h5>
        <p class="preview-text">{{ applyLog.path_adjustment || '—' }}</p>
        <h5>执行状态</h5>
        <p class="preview-text">
          Java 路径：{{ applyLog.java_path_applied ? '已成功' : '未执行/失败' }} ·
          路线同步：{{ applyLog.roadmap_synced ? '已同步' : '未同步' }} ·
          应用时间：{{ formatTime(applyLog.applied_at) }}
        </p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  generateEvaluation,
  listEvaluations,
  getEvaluationDetail,
  previewEvaluationAdjustment,
  syncEvaluationApply,
  getEvaluationApplyLog
} from '../api/evaluation'
import { applyEvaluationAdjustments, planPath } from '../api/path'
import { getStudentId } from '../api/auth'
import { getModuleMastery } from '../api/profileBuild'
import { trackBehavior } from '../api/behavior'
import { COURSE_NAME } from '../constants/course'
import ProfileRequiredAlert from '../components/ProfileRequiredAlert.vue'
import StageBalanceChart from '../components/StageBalanceChart.vue'
import WrongAnalysisPanel from '../components/WrongAnalysisPanel.vue'
import EvalHistoryCompareBar from '../components/EvalHistoryCompareBar.vue'
import { useRequiresProfile } from '../composables/useRequiresProfile'
import {
  enrichHistoryDeltas,
  buildEvalTrendSeries,
  getTrendFilterOptions,
  matchModuleFromText,
  formatDelta
} from '../utils/evaluationDashboard'

const router = useRouter()
const route = useRoute()
const studentId = computed(() => {
  const q = route.query.studentId
  if (q) return Number(q)
  return getStudentId() || 1
})
const { loading: profileLoading, profileCompleted } = useRequiresProfile()

const generating = ref(false)
const applying = ref(false)
const autoApply = ref(false)
const historyLoading = ref(false)
const currentReport = ref(null)
const prevReport = ref(null)
const history = ref([])
const applyLog = ref(null)
const previewVisible = ref(false)
const applyDetailVisible = ref(false)
const preview = ref(null)
const trendChartRef = ref(null)
const trendFilter = ref('total')
const trendEvalDetails = ref([])
let trendChart = null

const compareMode = ref(false)
const compareSelected = ref([])
const compareReports = ref([])

const stageDialogVisible = ref(false)
const stageDialogData = ref(null)

const trendFilterOptions = getTrendFilterOptions()

const displayMetrics = computed(() => currentReport.value?.metrics || {})
const stageBalance = computed(() => displayMetrics.value.stage_balance || [])
const scoreDelta = computed(() => currentReport.value?.score_delta ?? null)
const reportNo = computed(() => currentReport.value?.report_no || `RPT-${currentReport.value?.id || '-'}`)

const evalPeriodEnd = computed(() => currentReport.value?.created_at || null)
const evalPeriodStart = computed(() => {
  if (prevReport.value?.created_at) return prevReport.value.created_at
  if (!evalPeriodEnd.value) return null
  const d = new Date(evalPeriodEnd.value)
  d.setDate(d.getDate() - 30)
  return d.toISOString()
})

const trendPointCount = computed(() => trendEvalDetails.value.length)

const deltaClass = computed(() => {
  const d = scoreDelta.value
  if (d == null) return ''
  if (d > 0) return 'delta-up'
  if (d < 0) return 'delta-down'
  return ''
})

const stageDeltaClass = computed(() => {
  const d = stageDialogData.value?.delta
  if (d == null) return ''
  if (d > 0) return 'delta-up'
  if (d < 0) return 'delta-down'
  return ''
})

const stageDialogAttribution = computed(() => {
  if (!stageDialogData.value) return ''
  const name = stageDialogData.value.current.stage_name
  const weaknesses = currentReport.value?.report?.weaknesses || []
  const hit = weaknesses.find((w) => w.includes(name) || name.includes(w.slice(0, 6)))
  return hit || ''
})

function goPersonalizedResources() {
  router.push({
    path: '/resource/personalized',
    query: { trigger: 'assessment_complete', from: 'evaluation' }
  })
}

function formatTime(iso) {
  if (!iso) return '-'
  return String(iso).replace('T', ' ').slice(0, 16)
}

const TYPE_LABELS = { lecture: '讲义', exercise: '习题', courseware: '课件', exam_summary: '考点' }

function resourceTypeLabel(t) {
  return TYPE_LABELS[t] || t
}

function recommendModule(text) {
  const scores = displayMetrics.value.module_scores || []
  return matchModuleFromText(text, scores)
}

function goPractice(mod) {
  router.push({
    path: '/learn/exercise-center',
    query: { mode: 'module', moduleId: mod.module_id, from: 'evaluation' }
  })
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const data = await listEvaluations(studentId.value)
    history.value = enrichHistoryDeltas(data.items || [])
    await loadTrendEvalDetails()
  } finally {
    historyLoading.value = false
  }
}

async function loadTrendEvalDetails() {
  const items = [...history.value].sort((a, b) => a.id - b.id)
  if (!items.length) {
    trendEvalDetails.value = []
    return
  }
  const details = await Promise.all(items.map((item) => getEvaluationDetail(item.id)))
  trendEvalDetails.value = details.filter(Boolean)
  await nextTick()
  renderTrendChart()
}

async function loadPrevReport(reportId) {
  const idx = history.value.findIndex((h) => h.id === reportId)
  if (idx >= 0 && idx < history.value.length - 1) {
    const prevId = history.value[idx + 1].id
    prevReport.value = await getEvaluationDetail(prevId)
  } else {
    prevReport.value = null
  }
}

async function loadDetail(id) {
  const detail = await getEvaluationDetail(id)
  const histItem = history.value.find((h) => h.id === id)
  if (histItem?.score_delta != null) {
    detail.score_delta = histItem.score_delta
  } else if (history.value.length >= 2) {
    const idx = history.value.findIndex((h) => h.id === id)
    if (idx >= 0 && idx < history.value.length - 1) {
      const prev = history.value[idx + 1]
      detail.score_delta =
        Math.round((Number(detail.overall_score) - Number(prev.overall_score)) * 10) / 10
    }
  }
  currentReport.value = detail
  await loadPrevReport(id)
  await nextTick()
  renderTrendChart()
}

function renderTrendChart() {
  if (!trendChartRef.value) return
  const { labels, values, count } = buildEvalTrendSeries(trendEvalDetails.value, trendFilter.value)
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  if (count === 0) {
    trendChart.clear()
    return
  }

  trendChart.setOption({
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [
      {
        type: 'line',
        smooth: true,
        data: values,
        symbolSize: count < 2 ? 10 : 6,
        areaStyle: count >= 2 ? { opacity: 0.15 } : undefined
      }
    ]
  })
}

function openStageDialog(stage) {
  const prevStages = prevReport.value?.metrics?.stage_balance || []
  const prev = prevStages.find((s) => s.stage === stage.stage)
  const prevScore = prev ? prev.avg_score : null
  const delta =
    prevScore != null ? Math.round((stage.avg_score - prevScore) * 10) / 10 : null
  stageDialogData.value = { current: stage, prevScore, delta }
  stageDialogVisible.value = true
}

async function onGenerateConfirm() {
  try {
    await ElMessageBox.confirm(
      '将聚合练习、辅导、资源使用等数据生成本期诊断报告，并与上期报告进行对比。是否继续？',
      '生成周期性评估报告',
      { confirmButtonText: '确认生成', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }
  await onGenerate()
}

async function onGenerate() {
  generating.value = true
  try {
    currentReport.value = await generateEvaluation({ student_id: studentId.value, use_ai: true })
    trackBehavior(studentId.value, 'evaluation_generate', { eval_id: currentReport.value?.id })
    ElMessage.success('学习效果评估报告已生成')
    await loadHistory()
    await loadPrevReport(currentReport.value.id)
    await nextTick()
    renderTrendChart()
    if (autoApply.value) await openPreview()
  } catch (e) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function openPreview() {
  const adj = currentReport.value?.adjustment
  if (!adj) {
    ElMessage.warning('请先生成报告')
    return
  }
  preview.value = await previewEvaluationAdjustment(adj)
  previewVisible.value = true
}

async function confirmApply() {
  const adj = currentReport.value?.adjustment
  if (!adj) return
  applying.value = true
  let javaOk = false
  try {
    const payload = {
      studentId: studentId.value,
      subject: COURSE_NAME,
      weakModules: adj.weak_modules || [],
      pushStrategy: adj.push_strategy,
      pathAdjustment: adj.path_adjustment,
      recommendedActions: adj.recommended_actions,
      preferResourceTypes: adj.prefer_resource_types
    }
    try {
      await applyEvaluationAdjustments(payload)
      javaOk = true
    } catch {
      await planPath({ studentId: studentId.value, subject: COURSE_NAME })
      javaOk = true
    }
    const syncResult = await syncEvaluationApply({
      student_id: studentId.value,
      eval_id: currentReport.value?.id,
      adjustment: adj,
      java_ok: javaOk
    })
    applyLog.value = syncResult.log || syncResult
    previewVisible.value = false
    ElMessage.success('评估调整已应用，推送策略与学习计划已更新')
    trackBehavior(studentId.value, 'path_replan', { source: 'evaluation_apply' })
  } catch (e) {
    ElMessage.error(e.message || '应用失败')
  } finally {
    applying.value = false
  }
}

function onHistoryClick(item) {
  if (!compareMode.value) {
    loadDetail(item.id)
    return
  }
  toggleCompareSelect(item.id, !compareSelected.value.includes(item.id))
}

function toggleCompareMode() {
  compareMode.value = !compareMode.value
  if (!compareMode.value) {
    compareSelected.value = []
    compareReports.value = []
  }
}

function toggleCompareSelect(id, checked) {
  if (checked) {
    if (!compareSelected.value.includes(id)) {
      if (compareSelected.value.length >= 2) {
        compareSelected.value.shift()
      }
      compareSelected.value.push(id)
    }
  } else {
    compareSelected.value = compareSelected.value.filter((x) => x !== id)
  }
  refreshCompareReports()
}

async function refreshCompareReports() {
  if (compareSelected.value.length !== 2) {
    compareReports.value = []
    return
  }
  const sorted = [...compareSelected.value].sort((a, b) => a - b)
  const details = await Promise.all(sorted.map((id) => getEvaluationDetail(id)))
  compareReports.value = details.filter(Boolean)
}

function clearCompare() {
  compareSelected.value = []
  compareReports.value = []
  compareMode.value = false
}

async function loadApplyLog() {
  try {
    const data = await getEvaluationApplyLog(studentId.value)
    applyLog.value = data.log || null
  } catch {
    applyLog.value = null
  }
}

async function checkViewingStudentProfile() {
  if (route.query.studentId) {
    profileLoading.value = true
    try {
      const m = await getModuleMastery(studentId.value)
      profileCompleted.value = m.has_profile
    } catch {
      profileCompleted.value = false
    } finally {
      profileLoading.value = false
    }
  }
}

onMounted(async () => {
  await checkViewingStudentProfile()
  loadHistory()
  loadApplyLog()
})

onBeforeUnmount(() => {
  trendChart?.dispose()
})
</script>

<style scoped>
.evaluation-page {
  width: 100%;
  margin: 0 auto;
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
  margin-bottom: 8px;
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
.flow-desc {
  margin: 0;
  font-size: 13px;
  color: #606266;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.score-banner {
  display: flex;
  gap: 24px;
  align-items: center;
  margin-bottom: 12px;
}
.score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.score-num {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}
.score-label {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.9;
}
.score-summary p {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #606266;
}
.metric-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #909399;
}
.metric-row {
  margin-bottom: 12px;
}
.metric-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}
.metric-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}
.metric-tip {
  font-size: 14px;
  cursor: help;
  color: #c0c4cc;
}
.metric-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-top: 4px;
}
.delta-up {
  color: #67c23a;
}
.delta-down {
  color: #e6a23c;
}
.stage-hint {
  margin: 0 0 8px;
  font-size: 13px;
  color: #909399;
}
.stage-block {
  margin: 12px 0;
}
.stage-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.legend-dot--blue {
  background: #409eff;
}
.legend-dot--red {
  background: #f56c6c;
}
.legend-dot--gray {
  background: transparent;
  border: 1px dashed #909399;
  height: 0;
  width: 16px;
}
.trend-block {
  margin: 12px 0;
}
.trend-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.trend-select {
  width: 200px;
  flex-shrink: 0;
}
.trend-single-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 8px 10px;
  border-radius: 6px;
  line-height: 1.5;
}
.trend-block h4,
.section-title {
  margin: 0;
  font-size: 14px;
  color: #606266;
  font-weight: 600;
}
.trend-chart {
  height: 200px;
  width: 100%;
}
.text-list,
.recommend-list {
  padding-left: 20px;
  line-height: 1.8;
  color: #606266;
  margin: 0 0 12px;
}
.recommend-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.suggest-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: #909399;
}
.apply-log-wrap {
  margin: 16px 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.apply-log-alert {
  flex: 1;
}
.apply-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.history-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.compare-mode-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #409eff;
}
.history-item {
  display: flex;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  border: 1px solid #ebeef5;
  align-items: center;
}
.history-item:hover,
.history-item--active {
  background: #f0f9ff;
  border-color: #b3d8ff;
}
.history-check {
  flex-shrink: 0;
}
.history-score {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: #ecf5ff;
  color: #409eff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.history-tag {
  margin: 0 0 2px;
  font-size: 11px;
  color: #909399;
}
.history-summary {
  margin: 0 0 4px;
  font-size: 13px;
  color: #606266;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.history-time {
  font-size: 12px;
  color: #909399;
}
.history-tooltip p {
  margin: 0 0 4px;
  font-size: 12px;
  line-height: 1.5;
  max-width: 280px;
}
.empty-desc-title {
  margin: 0 0 4px;
  font-size: 14px;
  color: #606266;
}
.empty-desc-sub {
  margin: 0;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
.stage-dialog h4 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #303133;
}
.stage-compare-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.stage-compare-cell {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}
.cell-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.cell-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.stage-attribution {
  margin: 12px 0 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  background: #fdf6ec;
  padding: 8px 10px;
  border-radius: 6px;
}
.preview-body h5 {
  margin: 12px 0 6px;
  font-size: 13px;
  color: #303133;
}
.preview-intro {
  margin: 0 0 8px;
  font-size: 13px;
  color: #606266;
}
.preview-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
  line-height: 1.7;
  color: #606266;
}
.preview-text {
  margin: 0 0 8px;
  font-size: 13px;
  color: #606266;
}
.tag-gap {
  margin-right: 4px;
}
</style>
