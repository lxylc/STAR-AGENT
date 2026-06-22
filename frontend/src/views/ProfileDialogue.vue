<template>
  <div class="dialogue-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-head">
          <span>学习画像与答疑</span>
          <el-tag type="info">学生ID: {{ studentId }}</el-tag>
        </div>
      </template>

      <el-alert
        v-if="route.query.needProfile"
        title="请先完成学习画像构建"
        description="资源、路径、辅导与评估功能需在画像构建完成后使用。"
        type="warning"
        :closable="false"
        show-icon
        class="mb profile-hint-alert"
      />

      <el-tabs v-model="activeTab" class="mode-tabs" @tab-change="onTabChange">
        <el-tab-pane label="画像构建" name="build" />
      </el-tabs>

      <!-- 画像构建 -->
      <div v-show="activeTab === 'build'" class="chat-box" ref="buildChatRef">
        <template v-for="(msg, idx) in buildMessages" :key="msg.id || idx">
          <div
            v-if="msg.msg_type === 'text' || msg.msg_type === 'result'"
            :class="['msg-row', msg.role === 'user' ? 'user' : 'assistant']"
          >
            <div v-if="msg.role !== 'system'" class="avatar">
              {{ msg.role === 'user' ? '我' : 'AI' }}
            </div>
            <div class="bubble">
              <div>{{ msg.content }}</div>
              <div
                v-if="msg.msg_type === 'result' && msg.payload?.module_results"
                class="result-table"
              >
                <el-table :data="msg.payload.module_results" size="small" border>
                  <el-table-column prop="module_name" label="模块" />
                  <el-table-column prop="initial_level" label="自评" width="60" />
                  <el-table-column prop="correct_count" label="答对" width="60" />
                  <el-table-column prop="final_level" label="最终等级" width="80" />
                </el-table>
              </div>
            </div>
          </div>

          <div
            v-else-if="msg.msg_type === 'choice_card'"
            class="msg-row assistant"
          >
            <div class="avatar">AI</div>
            <div
              class="bubble choice-bubble"
              :class="{ 'choice-bubble--active': isActiveChoice(msg) }"
            >
              <div v-if="msg.payload?.module_name" class="choice-tag">
                {{ msg.payload.module_name }}
              </div>
              <div class="choice-prompt">{{ msg.content }}</div>
              <div class="choice-options">
                <el-button
                  v-for="opt in msg.payload?.options || []"
                  :key="opt.value"
                  :type="msg.payload?.selected === opt.value ? 'primary' : 'default'"
                  :disabled="!isActiveChoice(msg) || loading"
                  class="choice-btn"
                  round
                  @click="onChoice(msg, opt.value)"
                >
                  {{ opt.label }}
                </el-button>
              </div>
              <div v-if="msg.payload?.submitted" class="choice-done">已选择</div>
            </div>
          </div>

          <div
            v-else-if="msg.msg_type === 'basic_info' || msg.msg_type === 'module_assess' || msg.msg_type === 'exercise_quiz'"
            class="msg-row assistant legacy-hint"
          >
            <div class="avatar">AI</div>
            <div class="bubble muted">
              {{ msg.content }}
              <span class="legacy-tag">（历史会话，请重新生成画像以使用新流程）</span>
            </div>
          </div>
        </template>

        <div v-if="loading && activeTab === 'build'" class="loading-tip">
          <el-icon class="is-loading"><Loading /></el-icon> 处理中...
        </div>
      </div>

      <!-- 自评文本输入 -->
      <div v-if="activeTab === 'build' && expectsText && phase === 'assess'" class="qa-input-bar">
        <el-input
          v-model="assessText"
          type="textarea"
          :rows="3"
          placeholder="描述你对当前知识点的理解程度、练习感受…"
          :disabled="loading"
          @keydown.ctrl.enter="sendAssessText"
        />
        <el-button type="primary" :loading="loading" @click="sendAssessText">发送</el-button>
      </div>

      <div v-if="activeTab === 'build'" class="progress-bar">
        <span v-if="phase === 'assess'">自评进度：{{ moduleProgress.current }}/{{ moduleProgress.total }}</span>
        <span v-else-if="phase === 'quiz'">答题进度：{{ quizProgress.current }}/{{ quizProgress.total }}</span>
      </div>

      <div class="footer-actions">
        <el-tooltip
          v-if="buildInProgress"
          content="对话进行中，请通过上方选项或输入继续；完成后方可重新「开始构建」"
          placement="top"
        >
          <span>
            <el-button type="primary" :loading="loading" disabled @click="handleStartBuild">
              开始构建
            </el-button>
          </span>
        </el-tooltip>
        <el-button
          v-else
          type="primary"
          :loading="loading"
          @click="handleStartBuild"
        >
          开始构建
        </el-button>
        <el-button @click="goProfile">查看画像</el-button>
        <el-button type="warning" :loading="loading" :disabled="phase === 'assess' || phase === 'quiz'" @click="confirmRebuild">
          重新生成画像
        </el-button>
      </div>
      <p v-if="buildInProgress" class="footer-hint">对话进度已自动保存，可随时「查看画像」后返回继续</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  initBuildDialogue,
  rebuildProfile,
  submitDialogueStep,
  submitDialogueText
} from '../api/profileBuild'
import { getProfile } from '../api/profile'
import { getStudentId } from '../api/auth'

const router = useRouter()
const route = useRoute()
const studentId = getStudentId() || 1
const activeTab = ref('build')
const buildMessages = ref([])
const sessionId = ref('')
const phase = ref('welcome')
const expectsText = ref(false)
const assessText = ref('')
const moduleProgress = ref({ current: 0, total: 12 })
const quizProgress = ref({ current: 0, total: 12 })
const loading = ref(false)
const buildChatRef = ref(null)

/** 存在未完成会话时禁止再次「开始构建」，避免清空进度 */
const buildInProgress = computed(
  () => !!sessionId.value && phase.value !== 'done' && buildMessages.value.length > 0
)

function sessionStorageKey() {
  return `profile_build_session_${studentId}`
}

function persistSessionId(sid) {
  if (sid) localStorage.setItem(sessionStorageKey(), sid)
}

function scrollBottom(refEl) {
  nextTick(() => {
    if (refEl.value) {
      refEl.value.scrollTop = refEl.value.scrollHeight
    }
  })
}

function isActiveChoice(msg) {
  if (msg.payload?.submitted || phase.value === 'done') return false
  const cards = buildMessages.value.filter((m) => m.msg_type === 'choice_card')
  const last = cards[cards.length - 1]
  return last && last.id === msg.id
}

async function loadBuildSession(data) {
  if (data.session_id) {
    sessionId.value = data.session_id
    persistSessionId(data.session_id)
  }
  buildMessages.value = data.messages || []
  phase.value = data.phase || phase.value
  expectsText.value = !!data.expects_text
  if (data.module_index != null) {
    moduleProgress.value = {
      current: Math.min(data.module_index + 1, data.total_modules || 12),
      total: data.total_modules || 12
    }
  }
  if (data.phase === 'quiz') {
    const qi = data.quiz_index ?? (data.context_log || []).filter((c) => c.type === 'quiz_answer').length
    const total = data.quiz_total || 12
    quizProgress.value = { current: Math.min(qi + 1, total), total }
  }
  scrollBottom(buildChatRef)
}

async function sendAssessText() {
  const text = assessText.value.trim()
  if (!text || loading.value) return
  loading.value = true
  try {
    const res = await submitDialogueText({
      student_id: studentId,
      session_id: sessionId.value,
      text
    })
    assessText.value = ''
    await loadBuildSession(res)
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '提交失败')
  } finally {
    loading.value = false
  }
}

async function onChoice(msg, value) {
  if (!isActiveChoice(msg) || loading.value) return
  loading.value = true
  scrollBottom(buildChatRef)
  try {
    const res = await submitDialogueStep({
      student_id: studentId,
      session_id: sessionId.value,
      value
    })
    await loadBuildSession(res)
    if (res.phase === 'done') {
      ElMessage.success('学习画像已同步至「我的画像」')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '提交失败')
  } finally {
    loading.value = false
  }
}

async function handleStartBuild() {
  activeTab.value = 'build'
  if (buildInProgress.value) {
    ElMessage.warning('请先在当前对话中完成自评与答题，勿重复开始')
    return
  }
  const existing = await getProfile(studentId).catch(() => null)
  if (existing?.profileStatus === 'completed') {
    ElMessage.info('画像已存在，如需从头构建请点击「重新生成画像」')
    return
  }
  loading.value = true
  try {
    const data = await initBuildDialogue(studentId)
    await loadBuildSession(data)
    ElMessage.success(data.resumed ? '已恢复上次对话进度' : '已开始画像构建对话')
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '初始化失败，请确认 Flask 与 MongoDB 已启动')
  } finally {
    loading.value = false
  }
}

async function bootstrapBuild() {
  loading.value = true
  try {
    if (route.query.rebuild === '1') {
      const data = await rebuildProfile(studentId)
      await loadBuildSession(data)
      router.replace({ path: '/profile/dialogue' })
      ElMessage.success('已清空旧画像，请从对话开始重新填写')
      return
    }

    const existing = await getProfile(studentId).catch(() => null)
    if (existing?.profileStatus === 'completed') {
      buildMessages.value = [{
        id: 'completed-hint',
        role: 'assistant',
        msg_type: 'text',
        content:
          '您的学习画像已构建完成。可点击「查看画像」查看雷达图与掌握详情；'
          + '在「日常答疑」中提问将动态更新掌握度。如需从头重建，请点击「重新生成画像」。'
      }]
      phase.value = 'done'
      return
    }

    const data = await initBuildDialogue(studentId)
    await loadBuildSession(data)
    if (data.resumed) {
      ElMessage.info('已恢复上次未完成的画像构建对话')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '初始化失败，请确认 Flask 与 MongoDB 已启动')
  } finally {
    loading.value = false
  }
}

async function confirmRebuild() {
  try {
    await ElMessageBox.confirm(
      '将清空所有画像数据（含基本信息、知识点掌握与答疑记录），并从头重新构建。是否继续？',
      '重新生成画像',
      { type: 'warning', confirmButtonText: '确认清空', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  loading.value = true
  activeTab.value = 'build'
  try {
    const data = await rebuildProfile(studentId)
    localStorage.removeItem(sessionStorageKey())
    await loadBuildSession(data)
    qaMessages.value = []
    ElMessage.success('已清空全部数据，请重新开始构建')
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '重置失败')
  } finally {
    loading.value = false
  }
}

function onTabChange(name) {
  if (name === 'build') scrollBottom(buildChatRef)
}

function goProfile() {
  router.push('/profile/view')
}

onMounted(async () => {
  await bootstrapBuild()
})
</script>

<style scoped>
.dialogue-page {
  width: 100%;
  margin: 0 auto;
}
.mb {
  margin-bottom: 12px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mode-tabs {
  margin-bottom: 8px;
}
.chat-box {
  min-height: 480px;
  max-height: 68vh;
  overflow-y: auto;
  padding: 20px 16px;
  background: linear-gradient(180deg, #f5f7fb 0%, #eef1f6 100%);
  border-radius: 12px;
  margin-bottom: 12px;
}
.msg-row {
  display: flex;
  margin-bottom: 16px;
  gap: 10px;
  align-items: flex-start;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.msg-row.system {
  justify-content: center;
}
.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}
.msg-row.user .avatar {
  background: #67c23a;
}
.bubble {
  max-width: 82%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff;
  line-height: 1.65;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  font-size: 15px;
}
.msg-row.user .bubble {
  background: #e3f0ff;
}
.bubble-text {
  white-space: pre-wrap;
}
.choice-bubble {
  min-width: 260px;
  border: 1px solid #e4e7ed;
  background: linear-gradient(180deg, #fff 0%, #fafbfc 100%);
}
.choice-bubble--active {
  border-color: #409eff;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.15);
}
.choice-tag {
  display: inline-block;
  margin-bottom: 8px;
  padding: 2px 10px;
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  border-radius: 4px;
}
.choice-prompt {
  margin-bottom: 12px;
  font-weight: 500;
  color: #303133;
  white-space: pre-wrap;
}
.choice-done {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.choice-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.choice-btn {
  margin: 0 !important;
}
.bubble.muted {
  color: #909399;
  font-size: 13px;
}
.legacy-tag {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #c0c4cc;
}
.loading-tip {
  text-align: center;
  color: #909399;
  padding: 8px;
}
.progress-bar {
  padding: 8px 12px;
  color: #606266;
  font-size: 13px;
  border-top: 1px solid #ebeef5;
}
.footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.footer-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #909399;
}
.result-table {
  margin-top: 10px;
}
</style>
