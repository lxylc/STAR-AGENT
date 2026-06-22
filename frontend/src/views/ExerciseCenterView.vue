<template>
  <div class="exercise-center" v-loading="loading">
    <ProfileRequiredAlert :loading="profileLoading" :profile-completed="profileCompleted" />

    <template v-if="profileCompleted">
      <el-card shadow="never" class="head-card">
        <template #header>
          <div class="card-head">
            <span>统一习题中心</span>
            <el-button link type="primary" @click="goBack">返回</el-button>
          </div>
        </template>
        <p class="head-desc">
          专项习题、模块训练、错题重做、学习路线配套习题 — 按四个学习阶段、十二章节分类练习。
        </p>
        <div v-if="overview" class="overview-row">
          <el-tag type="danger" effect="plain">错题 {{ overview.wrong_count }} 道</el-tag>
          <el-tag
            v-for="m in overview.weak_modules"
            :key="m.module_id"
            effect="plain"
            type="warning"
          >
            {{ m.module_name }} · {{ m.score }}分
          </el-tag>
        </div>
      </el-card>

      <el-card
        v-if="overview?.weekly_overview && !activeMode && !pickingChapter && !questions.length"
        shadow="never"
        class="week-card"
      >
        <template #header>
          <div class="card-head">
            <span>本周刷题学情总览</span>
            <span class="week-range">{{ overview.weekly_overview.week_label }}</span>
          </div>
        </template>
        <p class="week-rule">{{ overview.weekly_overview.time_rule }}</p>
        <div class="week-metrics">
          <div class="week-metric">
            <span class="metric-value">{{ overview.weekly_overview.total_count }}</span>
            <span class="metric-label">本周完成总做题量</span>
          </div>
          <div class="week-metric">
            <span class="metric-value">{{ overview.weekly_overview.accuracy_pct }}%</span>
            <span class="metric-label">本周习题平均正确率</span>
          </div>
          <div class="week-metric">
            <span class="metric-value metric-value--text">
              {{ overview.weekly_overview.weak_module?.module_name || '暂无' }}
            </span>
            <span class="metric-label">
              本周高频薄弱知识点
              <template v-if="overview.weekly_overview.weak_module">
                （错题 {{ overview.weekly_overview.weak_module.wrong_count }} 道）
              </template>
            </span>
          </div>
          <div class="week-metric">
            <span class="metric-value">{{ overview.weekly_overview.new_wrong_count }}</span>
            <span class="metric-label">本周新增错题数量</span>
          </div>
        </div>
      </el-card>

      <el-card v-if="!activeMode && !pickingChapter && !questions.length" shadow="never">
        <div class="entry-grid">
          <div
            v-for="entry in overview?.entries || []"
            :key="entry.mode"
            class="entry-card"
            @click="selectMode(entry.mode)"
          >
            <h4>{{ entry.label }}</h4>
            <p>{{ entry.desc }}</p>
          </div>
        </div>
      </el-card>

      <el-card
        v-if="!activeMode && !pickingChapter && !questions.length && chapterProgressList.length"
        shadow="never"
        class="chapter-progress-card"
      >
        <template #header>
          <span>全章节进度</span>
        </template>
        <el-table :data="chapterProgressList" stripe class="chapter-progress-table">
          <el-table-column prop="chapter_no" label="章节" width="72" align="center">
            <template #default="{ row }">第 {{ row.chapter_no }} 章</template>
          </el-table-column>
          <el-table-column prop="module_name" label="模块名称" min-width="160" />
          <el-table-column prop="stage_name" label="学习阶段" width="140" />
          <el-table-column label="掌握分" width="88" align="center">
            <template #default="{ row }">
              <span v-if="row.final_score != null" :class="`score-text score-text--${scoreLevel(row.final_score)}`">
                {{ row.final_score }}
              </span>
              <span v-else class="score-text score-text--none">—</span>
            </template>
          </el-table-column>
          <el-table-column label="本周做题" width="88" align="center">
            <template #default="{ row }">{{ row.week_practice_count || 0 }} 道</template>
          </el-table-column>
          <el-table-column label="专项题" width="80" align="center">
            <template #default="{ row }">{{ row.stats?.special?.question_count || 0 }}</template>
          </el-table-column>
          <el-table-column label="错题" width="72" align="center">
            <template #default="{ row }">
              <span :class="{ 'wrong-count': row.stats?.wrong?.wrong_count }">
                {{ row.stats?.wrong?.wrong_count || 0 }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="路线" width="88" align="center">
            <template #default="{ row }">
              {{ row.stats?.roadmap?.day ? `Day ${row.stats.roadmap.day}` : '—' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card v-if="pickingChapter && !questions.length" shadow="never">
        <template #header>
          <div class="card-head">
            <span>{{ modeLabel }} · 选择章节</span>
            <el-button link type="primary" @click="backToModes">返回模式选择</el-button>
          </div>
        </template>
        <p class="chapter-hint">按课程四个学习阶段选择章节，进入对应练习。</p>
        <div v-for="stage in overview?.chapter_stages || []" :key="stage.stage" class="chapter-stage">
          <h4 class="stage-title">{{ stage.stage_name }}</h4>
          <div class="chapter-grid">
            <button
              v-for="ch in stage.chapters"
              :key="ch.module_id"
              type="button"
              class="chapter-card"
              :class="{
                'chapter-card--disabled': !chapterAvailable(ch),
                [`chapter-card--${scoreLevel(ch.final_score)}`]: ch.final_score != null
              }"
              :disabled="!chapterAvailable(ch)"
              @click="selectChapter(ch)"
            >
              <span class="chapter-no">第 {{ ch.chapter_no }} 章</span>
              <span class="chapter-name">{{ ch.module_name }}</span>
              <span v-if="ch.final_score != null" class="chapter-score">{{ ch.final_score }} 分</span>
              <span class="chapter-badge">{{ chapterBadge(ch) }}</span>
            </button>
          </div>
        </div>
        <el-empty v-if="!(overview?.chapter_stages || []).length" description="暂无章节数据" />
      </el-card>

      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="false"
        class="practice-alert"
      />

      <el-card v-if="generating" shadow="never">
        <el-empty description="正在加载本批专项习题…" />
      </el-card>

      <el-alert
        v-if="fallbackNotice && questions.length"
        :title="fallbackNotice"
        type="warning"
        show-icon
        :closable="false"
        class="practice-alert"
      />

      <template v-if="!generating && questions.length">
        <el-card shadow="never">
          <template #header>
            <div class="card-head">
              <span>
                {{ modeLabel }} · 共 {{ questions.length }} 题
                <el-tag v-if="meta.module_name" size="small" class="ml-8">{{ meta.module_name }}</el-tag>
              </span>
              <el-button v-if="!submitted" link type="primary" :loading="regenerating" @click="reload">
                重新加载
              </el-button>
            </div>
          </template>

          <div class="question-list">
            <div
              v-for="(q, idx) in questions"
              :key="q.qid"
              class="question-card"
              :class="{ 'question-card--review': submitted }"
            >
              <div class="q-head">
                <span class="q-no">第 {{ idx + 1 }} 题</span>
                <el-tag size="small">{{ typeLabel(q.type) }}</el-tag>
                <el-tag
                  v-if="submitted && resultMap[q.qid]"
                  size="small"
                  :type="judgeTagType(resultMap[q.qid])"
                >
                  {{ resultMap[q.qid].judge_label }}
                </el-tag>
              </div>
              <p class="q-content">{{ q.content }}</p>

              <el-radio-group
                v-if="q.type === 'choice'"
                v-model="answers[q.qid]"
                class="q-choice"
                :disabled="submitted"
              >
                <el-radio
                  v-for="(val, key) in q.options || {}"
                  :key="key"
                  :value="key"
                  class="q-radio"
                >
                  <strong>{{ key }}.</strong> {{ val }}
                </el-radio>
              </el-radio-group>

              <el-checkbox-group
                v-else-if="q.type === 'multi_choice'"
                v-model="answers[q.qid]"
                class="q-choice"
                :disabled="submitted"
              >
                <el-checkbox
                  v-for="(val, key) in q.options || {}"
                  :key="key"
                  :value="key"
                  class="q-radio"
                >
                  <strong>{{ key }}.</strong> {{ val }}
                </el-checkbox>
              </el-checkbox-group>

              <el-radio-group
                v-else-if="q.type === 'judge'"
                v-model="answers[q.qid]"
                :disabled="submitted"
              >
                <el-radio value="对">对</el-radio>
                <el-radio value="错">错</el-radio>
              </el-radio-group>

              <PythonCodeEditor
                v-else-if="q.type === 'coding'"
                v-model="answers[q.qid]"
                :readonly="submitted"
                min-height="260px"
              />
              <el-input
                v-else
                v-model="answers[q.qid]"
                type="textarea"
                :rows="3"
                placeholder="请输入你的答案…"
                :disabled="submitted"
                class="q-textarea"
              />

              <div v-if="submitted && resultMap[q.qid]" class="review-block">
                <p v-if="resultMap[q.qid].user_answer" class="review-line">
                  <span class="label">你的作答：</span>{{ resultMap[q.qid].user_answer }}
                </p>
                <p class="review-line answer">
                  <span class="label">参考答案：</span>{{ resultMap[q.qid].correct_answer }}
                </p>
                <p v-if="resultMap[q.qid].judge_reason" class="review-line analysis">
                  <span class="label">评判：</span>{{ resultMap[q.qid].judge_reason }}
                  <span v-if="resultMap[q.qid].judge_method === 'ai'" class="judge-tag">（AI 评判）</span>
                </p>
                <p v-if="resultMap[q.qid].analysis" class="review-line analysis">
                  <span class="label">解析：</span>{{ resultMap[q.qid].analysis }}
                </p>
              </div>
            </div>
          </div>
        </el-card>

        <div class="practice-actions">
          <template v-if="!submitted">
            <el-button type="primary" size="large" :loading="submitting" @click="handleSubmit">
              提交批改
            </el-button>
          </template>
          <template v-else>
            <el-alert
              :title="result.message"
              type="success"
              show-icon
              :closable="false"
              class="result-alert"
            />
            <p v-if="result.removed_wrong_count" class="score-change">
              已从错题本移除 <strong>{{ result.removed_wrong_count }}</strong> 道题
            </p>
            <p v-if="result.profile_update" class="score-change">
              模块分数：{{ result.profile_update.old_score }} →
              <strong>{{ result.profile_update.new_score }}</strong>
            </p>
            <el-button type="primary" @click="goBack">返回</el-button>
            <el-button @click="reload">再来一组</el-button>
          </template>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ProfileRequiredAlert from '../components/ProfileRequiredAlert.vue'
import PythonCodeEditor from '../components/PythonCodeEditor.vue'
import { useRequiresProfile } from '../composables/useRequiresProfile'
import {
  getExerciseCenterOverview,
  generateExerciseSession,
  submitExerciseSession
} from '../api/profileBuild'
import { getStudentId } from '../api/auth'

const route = useRoute()
const router = useRouter()
const studentId = getStudentId() || 1
const { loading: profileLoading, profileCompleted } = useRequiresProfile()

const loading = ref(false)
const generating = ref(false)
const regenerating = ref(false)
const submitting = ref(false)
const submitted = ref(false)
const errorMsg = ref('')
const overview = ref(null)
const activeMode = ref('')
const pickingChapter = ref(false)
const sessionId = ref('')
const questions = ref([])
const answers = reactive({})
const result = ref({})
const fallbackNotice = ref('')

const meta = reactive({
  module_name: '',
  module_id: null,
  mode_label: ''
})

const resultMap = computed(() => {
  const map = {}
  for (const r of result.value.results || []) {
    map[r.qid] = r
  }
  return map
})

const modeLabel = computed(() => {
  if (meta.mode_label) return meta.mode_label
  const entry = (overview.value?.entries || []).find((e) => e.mode === activeMode.value)
  return entry?.label || activeMode.value || '习题练习'
})

const chapterProgressList = computed(() => {
  const list = []
  for (const stage of overview.value?.chapter_stages || []) {
    for (const ch of stage.chapters || []) {
      list.push({ ...ch, stage_name: stage.stage_name })
    }
  }
  return list
})

function scoreLevel(score) {
  if (score == null) return 'none'
  if (score >= 85) return 'high'
  if (score >= 45) return 'mid'
  return 'low'
}

function chapterStat(ch, mode) {
  return ch?.stats?.[mode] || {}
}

function chapterAvailable(ch) {
  const mode = activeMode.value
  if (!mode) return false
  const stat = chapterStat(ch, mode)
  if (mode === 'module') return stat.available !== false
  return !!stat.available
}

function chapterBadge(ch) {
  const mode = activeMode.value
  const stat = chapterStat(ch, mode)
  if (mode === 'special') {
    const n = stat.question_count || 0
    if (!n) return '待一键生成'
    return `${n} 道题`
  }
  if (mode === 'module') return 'AI 出题'
  if (mode === 'wrong') {
    const n = stat.wrong_count || 0
    return n ? `${n} 道错题` : '无错题'
  }
  if (mode === 'roadmap') {
    return stat.day ? `Day ${stat.day}` : '未在路线中'
  }
  return ''
}

function backToModes() {
  pickingChapter.value = false
  activeMode.value = ''
  router.replace({ path: '/learn/exercise-center', query: { from: route.query.from } })
}

function selectChapter(ch) {
  if (!chapterAvailable(ch)) return
  const stat = chapterStat(ch, activeMode.value)
  startSession(activeMode.value, {
    moduleId: ch.module_id,
    day: stat.day || null
  })
}

const TYPE_LABELS = {
  choice: '单选题',
  multi_choice: '多选题',
  judge: '判断题',
  short: '简答题',
  coding: '编程题'
}

function typeLabel(t) {
  return TYPE_LABELS[t] || t
}

function judgeTagType(result) {
  if (result?.is_correct) return 'success'
  if (result?.is_partial) return 'warning'
  return 'danger'
}

function parseQuery() {
  return {
    mode: route.query.mode || '',
    moduleId: Number(route.query.moduleId || route.query.module_id) || null,
    day: Number(route.query.day) || null,
    resourceId: route.query.resourceId ? String(route.query.resourceId) : '',
    itemIds: route.query.itemIds
      ? String(route.query.itemIds).split(',').filter(Boolean)
      : route.query.item_id
        ? [String(route.query.item_id)]
        : [],
    kpId: Number(route.query.kpId) || null
  }
}

function goBack() {
  const from = route.query.from
  if (from === 'wrong_review') {
    router.push('/learn/wrong-review')
  } else if (from === 'resource') {
    router.push('/resource/personalized')
  } else {
    router.push('/profile/view')
  }
}

function resetAnswers(qs) {
  Object.keys(answers).forEach((k) => delete answers[k])
  for (const q of qs) {
    answers[q.qid] = q.type === 'multi_choice' ? [] : ''
  }
}

function formatAnswerForSubmit(q) {
  const raw = answers[q.qid]
  if (q.type === 'multi_choice') {
    const arr = Array.isArray(raw) ? raw : []
    return [...arr].sort().join(',')
  }
  return (raw ?? '').toString()
}

async function loadOverview() {
  try {
    overview.value = await getExerciseCenterOverview(studentId)
  } catch {
    /* 概览失败不阻断做题 */
  }
}

async function startSession(mode, opts = {}) {
  const q = parseQuery()
  const mid = opts.moduleId || q.moduleId
  if (mode !== 'wrong' && !mid) {
    ElMessage.warning('请先选择章节')
    return
  }
  if (mode === 'module' && !mid) {
    ElMessage.warning('模块训练需要指定章节')
    return
  }

  errorMsg.value = ''
  fallbackNotice.value = ''
  submitted.value = false
  result.value = {}
  activeMode.value = mode
  pickingChapter.value = false
  generating.value = true

  try {
    const payload = {
      student_id: studentId,
      mode,
      module_id: mid,
      day: opts.day || q.day,
      kp_id: q.kpId,
      item_ids: opts.itemIds || q.itemIds,
      resource_id: opts.resourceId || q.resourceId || undefined
    }
    const data = await generateExerciseSession(payload)
    sessionId.value = data.session_id
    questions.value = data.questions || []
    meta.module_name = data.module_name
    meta.module_id = data.module_id
    meta.mode_label = data.mode_label || mode
    fallbackNotice.value = data.fallback_notice || ''
    resetAnswers(questions.value)
  } catch (e) {
    errorMsg.value = e?.response?.data?.error || e?.message || '加载题目失败'
  } finally {
    generating.value = false
  }
}

function selectMode(mode) {
  const q = parseQuery()
  activeMode.value = mode
  meta.mode_label = (overview.value?.entries || []).find((e) => e.mode === mode)?.label || mode

  if (q.moduleId) {
    const day = q.day || findChapterDay(q.moduleId)
    startSession(mode, { moduleId: q.moduleId, day })
    return
  }

  pickingChapter.value = true
  router.replace({
    path: '/learn/exercise-center',
    query: { mode, from: route.query.from || 'center' }
  })
}

function findChapterDay(moduleId) {
  for (const stage of overview.value?.chapter_stages || []) {
    for (const ch of stage.chapters || []) {
      if (ch.module_id === moduleId) {
        return ch.stats?.roadmap?.day || null
      }
    }
  }
  return null
}

async function reload(isRegen = true) {
  if (isRegen) regenerating.value = true
  const q = parseQuery()
  await startSession(activeMode.value || q.mode || 'special', {
    moduleId: meta.module_id || q.moduleId,
    day: q.day,
    itemIds: q.itemIds
  })
  regenerating.value = false
}

function isAnswered(q) {
  const raw = answers[q.qid]
  if (q.type === 'multi_choice') {
    return Array.isArray(raw) && raw.length > 0
  }
  return String(raw ?? '').trim().length > 0
}

async function handleSubmit() {
  const unanswered = questions.value.filter((q) => !isAnswered(q))
  if (unanswered.length) {
    ElMessage.warning(`还有 ${unanswered.length} 题未作答`)
    return
  }
  submitting.value = true
  try {
    result.value = await submitExerciseSession({
      student_id: studentId,
      session_id: sessionId.value,
      answers: questions.value.map((q) => ({
        qid: q.qid,
        answer: formatAnswerForSubmit(q)
      }))
    })
    submitted.value = true
    ElMessage.success('批改完成，数据已同步至画像')
    await loadOverview()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || e?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (!profileCompleted.value) return
  await loadOverview()
  await bootstrapFromQuery()
})

watch(profileCompleted, async (completed) => {
  if (completed) {
    await loadOverview()
    await bootstrapFromQuery()
  }
})

async function bootstrapFromQuery() {
  const q = parseQuery()
  if (!q.mode) return
  activeMode.value = q.mode
  meta.mode_label =
    (overview.value?.entries || []).find((e) => e.mode === q.mode)?.label || q.mode
  if (q.moduleId || q.itemIds.length) {
    await startSession(q.mode, { moduleId: q.moduleId, itemIds: q.itemIds, day: q.day })
    return
  }
  pickingChapter.value = true
}
</script>

<style scoped>
.exercise-center {
  width: 100%;
  margin: 0 auto;
  padding-bottom: 40px;
}
.head-card {
  margin-bottom: 16px;
}
.week-card {
  margin-bottom: 16px;
}
.week-range {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}
.week-rule {
  margin: 0 0 16px;
  font-size: 12px;
  color: #909399;
}
.week-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}
.week-metric {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafafa;
}
.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  line-height: 1.3;
}
.metric-value--text {
  font-size: 15px;
  font-weight: 600;
}
.metric-label {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}
.chapter-progress-card {
  margin-top: 16px;
}
.chapter-progress-table {
  width: 100%;
}
.score-text--high {
  color: #67c23a;
  font-weight: 600;
}
.score-text--mid {
  color: #e6a23c;
  font-weight: 600;
}
.score-text--low {
  color: #f56c6c;
  font-weight: 600;
}
.score-text--none {
  color: #c0c4cc;
}
.wrong-count {
  color: #f56c6c;
  font-weight: 600;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.head-desc {
  margin: 0 0 12px;
  font-size: 14px;
  color: #606266;
}
.overview-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.entry-card {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.entry-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
}
.entry-card h4 {
  margin: 0 0 8px;
  font-size: 15px;
}
.entry-card p {
  margin: 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}
.chapter-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: #909399;
}
.chapter-stage {
  margin-bottom: 20px;
}
.stage-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.chapter-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 14px;
  text-align: left;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.chapter-card:hover:not(:disabled) {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
}
.chapter-card--disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.chapter-card--high {
  border-left: 3px solid #67c23a;
}
.chapter-card--mid {
  border-left: 3px solid #e6a23c;
}
.chapter-card--low {
  border-left: 3px solid #f56c6c;
}
.chapter-no {
  font-size: 12px;
  color: #909399;
}
.chapter-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
}
.chapter-score {
  font-size: 12px;
  color: #606266;
}
.chapter-badge {
  font-size: 12px;
  color: #409eff;
  margin-top: 2px;
}
.practice-alert {
  margin-bottom: 16px;
}
.ml-8 {
  margin-left: 8px;
}
.question-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.question-card {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.question-card--review {
  background: #fff;
}
.q-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.q-no {
  font-weight: 600;
  font-size: 14px;
}
.q-content {
  margin: 0 0 12px;
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
}
.q-choice {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
.q-radio {
  display: flex;
  align-items: flex-start;
  white-space: normal;
  height: auto;
  line-height: 1.6;
}
.review-block {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
}
.review-line {
  margin: 0 0 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.review-line.answer {
  color: #529b2e;
  background: #f0f9eb;
  padding: 6px 10px;
  border-radius: 6px;
}
.review-line.analysis {
  color: #b88230;
  background: #fdf6ec;
  padding: 6px 10px;
  border-radius: 6px;
}
.judge-tag {
  font-size: 12px;
  color: #909399;
}
.label {
  font-weight: 600;
}
.practice-actions {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}
.result-alert {
  width: 100%;
}
.score-change {
  margin: 0;
  font-size: 14px;
  color: #303133;
}
</style>
