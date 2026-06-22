<template>
  <div class="practice-page" v-loading="loading">
    <div class="practice-head">
      <el-button link type="primary" @click="goBack">← 返回画像</el-button>
      <h2 class="practice-title">模块练习</h2>
      <p v-if="meta.module_name" class="practice-sub">
        {{ meta.module_name }}
        <el-tag v-if="meta.current_score != null" size="small" type="info">
          当前 {{ meta.current_score }} 分
        </el-tag>
        <el-tag v-if="submitted" size="small" :type="scoreTagType">
          本次 {{ result.practice_score }} 分
        </el-tag>
      </p>
    </div>

    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      :closable="false"
      class="practice-alert"
    />

    <el-card v-if="generating" shadow="never">
      <el-empty description="题库智能体正在生成题目，请稍候…" />
    </el-card>

    <template v-else-if="questions.length">
      <el-card shadow="never">
        <template #header>
          <div class="card-head">
            <span>共 {{ questions.length }} 题 · 无计时 · 自由作答</span>
            <el-button v-if="!submitted" link type="primary" :loading="regenerating" @click="regenerate">
              重新生成
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

            <!-- 单选 -->
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

            <!-- 判断 -->
            <el-radio-group
              v-else-if="q.type === 'judge'"
              v-model="answers[q.qid]"
              :disabled="submitted"
            >
              <el-radio value="对">对</el-radio>
              <el-radio value="错">错</el-radio>
            </el-radio-group>

            <!-- 简答 / 编程 -->
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
          <p v-if="result.profile_update" class="score-change">
            模块分数：{{ result.profile_update.old_score }} →
            <strong>{{ result.profile_update.new_score }}</strong>
            （{{ deltaText }}）
          </p>
          <el-button type="primary" @click="goBack">返回画像查看更新</el-button>
          <el-button @click="regenerate">再来一组</el-button>
        </template>
      </div>
    </template>

    <el-empty v-else-if="!loading && !generating" description="暂无题目">
      <el-button type="primary" @click="loadQuestions">生成题目</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { generateModulePractice, submitModulePractice } from '../api/profileBuild'
import PythonCodeEditor from '../components/PythonCodeEditor.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const generating = ref(false)
const regenerating = ref(false)
const submitting = ref(false)
const submitted = ref(false)
const errorMsg = ref('')

const sessionId = ref('')
const questions = ref([])
const answers = reactive({})
const result = ref({})
const resultMap = computed(() => {
  const map = {}
  for (const r of result.value.results || []) {
    map[r.qid] = r
  }
  return map
})

const meta = reactive({
  module_name: '',
  module_id: null,
  current_score: null
})

const scoreTagType = computed(() => {
  const s = result.value.practice_score
  if (s >= 80) return 'success'
  if (s >= 60) return 'warning'
  return 'danger'
})

const deltaText = computed(() => {
  const d = result.value.profile_update?.score_delta
  if (d == null) return ''
  if (d > 0) return `+${d}`
  if (d < 0) return String(d)
  return '持平'
})

const TYPE_LABELS = {
  choice: '单选题',
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

function studentId() {
  return Number(route.query.studentId || route.query.student_id)
}

function moduleId() {
  return Number(route.query.moduleId || route.query.module_id)
}

function goBack() {
  const sid = studentId()
  router.push(sid ? { path: '/profile/view', query: { studentId: sid } } : '/profile/view')
}

function resetAnswers(qs) {
  Object.keys(answers).forEach((k) => delete answers[k])
  for (const q of qs) {
    answers[q.qid] = ''
  }
}

async function loadQuestions(isRegen = false) {
  const sid = studentId()
  const mid = moduleId()
  if (!sid || !mid) {
    errorMsg.value = '缺少学生或模块参数'
    return
  }

  errorMsg.value = ''
  submitted.value = false
  result.value = {}
  if (isRegen) regenerating.value = true
  else {
    loading.value = true
    generating.value = true
  }

  try {
    const data = await generateModulePractice({
      student_id: sid,
      module_id: mid,
      source: route.query.source || route.query.tagType || 'profile'
    })
    sessionId.value = data.session_id
    questions.value = data.questions || []
    meta.module_name = data.module_name
    meta.module_id = data.module_id
    meta.current_score = data.current_score
    resetAnswers(questions.value)
  } catch (e) {
    errorMsg.value = e?.response?.data?.error || e?.message || '出题失败'
  } finally {
    loading.value = false
    generating.value = false
    regenerating.value = false
  }
}

function regenerate() {
  loadQuestions(true)
}

async function handleSubmit() {
  const unanswered = questions.value.filter((q) => !(answers[q.qid] || '').toString().trim())
  if (unanswered.length) {
    ElMessage.warning(`还有 ${unanswered.length} 题未作答`)
    return
  }

  submitting.value = true
  try {
    const payload = {
      student_id: studentId(),
      session_id: sessionId.value,
      answers: questions.value.map((q) => ({
        qid: q.qid,
        answer: answers[q.qid]
      }))
    }
    result.value = await submitModulePractice(payload)
    submitted.value = true
    ElMessage.success('批改完成，分数已同步至画像')
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || e?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => loadQuestions())
</script>

<style scoped>
.practice-page {
  width: 100%;
  padding: 0 0 40px;
}
.practice-head {
  margin-bottom: 20px;
}
.practice-title {
  margin: 8px 0 4px;
  font-size: 20px;
  font-weight: 600;
}
.practice-sub {
  margin: 0;
  font-size: 14px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.practice-alert {
  margin-bottom: 16px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
.q-textarea {
  margin-top: 4px;
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
