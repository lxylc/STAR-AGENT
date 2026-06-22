<template>

  <div class="agent-chat" v-loading="loading">

    <header class="chat-top">
      <div class="chat-heading">
        <h1 class="panel-title">Python 学习智能体</h1>
        <p class="panel-subtitle">概念 · 代码 · 错题 · 深入讨论</p>
      </div>
      <button
        type="button"
        class="new-session-btn"
        title="新会话"
        aria-label="新会话"
        @click="startNewSession"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </header>



    <div

      class="content-card"

      ref="contentRef"

      @mouseup="onTextSelect"

    >

      <div v-if="showHistory" class="history-block">

        <h4 class="section-label">历史记录</h4>

        <div v-for="(msg, idx) in messages" :key="'h-' + (msg.id || idx)" class="history-line">

          <span class="history-role">{{ msg.role === 'user' ? '我' : 'AI' }}</span>

          <span class="history-snippet">{{ snippet(msg) }}</span>

        </div>

        <p v-if="!messages.length" class="empty-hint">暂无历史消息</p>

      </div>



      <template v-else>

        <div v-if="!displayMessages.length && !loading" class="welcome">

          <h2 class="welcome-title">Python 学习智能体</h2>

          <p>你好，我是你的学习助手。可以问我概念、代码、错题，或结合当前学习内容深入讨论。</p>

          <ul class="welcome-list">

            <li>在正文中拖选文字，右侧将联动显示解释</li>

            <li>使用底部输入框提问，支持 Ctrl + Enter 发送</li>

          </ul>

        </div>



        <article

          v-for="(msg, idx) in displayMessages"

          :key="msg.id || idx"

          :class="['content-block', msg.role]"

        >

          <p v-if="msg.role === 'user'" class="user-question">{{ msg.content }}</p>



          <template v-else-if="msg.msg_type === 'mastery_update'">

            <p class="system-note">{{ msg.content }}</p>

          </template>



          <template v-else-if="msg.msg_type === 'tutoring_answer'">

            <TutoringAnswerBlock

              :payload="msg.payload"

              :fallback-content="msg.content"

              :media-loading="mediaLoadingId === (msg.id || idx)"

              @follow-up="onFollowUp"

              @generate-media="onGenerateMedia(msg, idx)"

            />

          </template>



          <div v-else class="rich-text">{{ msg.content }}</div>

        </article>



        <p v-if="asking" class="typing">正在思考…</p>

      </template>

    </div>



    <footer class="chat-input-bar">

      <div class="input-shell">

        <el-input

          v-model="question"

          type="textarea"

          :rows="1"

          :autosize="{ minRows: 1, maxRows: 4 }"

          placeholder="输入你的问题…"

          :disabled="asking"

          resize="none"

          class="round-input"

          @keydown.ctrl.enter.prevent="sendQuestion"

        />

        <button

          type="button"

          class="send-icon-btn"

          :disabled="asking || !question.trim()"

          aria-label="发送"

          @click="sendQuestion"

        >

          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">

            <path d="M5 12h12M13 6l6 6-6 6" />

          </svg>

        </button>

      </div>

      <div class="input-meta">

        <el-select v-model="answerMode" size="small" class="mode-select">

          <el-option label="全部形式" value="all" />

          <el-option label="仅文字" value="text" />

          <el-option label="文字+图解" value="diagram" />

          <el-option label="文字+视频" value="video" />

        </el-select>

        <span v-if="contextLabel" class="context-chip">{{ contextLabel }}</span>

      </div>

    </footer>

  </div>

</template>



<script setup>

import { ref, computed, watch, nextTick } from 'vue'

import { useRoute, useRouter } from 'vue-router'

import { ElMessage } from 'element-plus'

import { initTutoring, createTutoringSession, askTutoring, generateTutoringMedia } from '../api/tutoring'

import { getStudentId } from '../api/auth'

import { trackBehavior } from '../api/behavior'

import { syncPathFromProfile } from '../api/path'

import { COURSE_NAME } from '../constants/course'

import TutoringAnswerBlock from './TutoringAnswerBlock.vue'

import { normalizeTutoringPayload } from '../utils/tutoring'



const emit = defineEmits(['selection-change', 'related-update'])



const route = useRoute()

const router = useRouter()

const studentId = getStudentId() || 1



const subjectTrack = 'engineering'



const messages = ref([])

const sessionId = ref('')

const question = ref('')

const answerMode = ref('all')

const loading = ref(false)

const asking = ref(false)

const mediaLoadingId = ref(null)

const contentRef = ref(null)



const showHistory = computed(() => route.query.view === 'history')



const context = computed(() => {

  const c = {}

  if (route.query.kp) c.knowledge_point = route.query.kp

  if (route.query.title) c.resource_title = route.query.title

  if (route.query.excerpt) c.resource_excerpt = route.query.excerpt

  return Object.keys(c).length ? c : null

})



const contextLabel = computed(() => {

  if (!context.value) return ''

  return context.value.resource_title || context.value.knowledge_point || '带上下文'

})



const displayMessages = computed(() => {

  if (showHistory.value) return []

  return messages.value.filter((m) => {
    if (m.msg_type === 'tutoring_welcome') return false
    return m.role !== 'system' || m.msg_type
  })

})



const latestRelated = computed(() => {

  for (let i = messages.value.length - 1; i >= 0; i--) {

    const p = messages.value[i]?.payload

    if (p?.related_kps?.length) {

      return p.related_kps.map((kp) => `巩固练习：${kp}`)

    }

    if (p?.follow_up_actions?.length) {

      return p.follow_up_actions.map((a) => a.label)

    }

  }

  return [

    '变量与数据类型的定义与区别？',

    '如何用 input() 读取用户输入？',

    'for 循环与 while 循环的适用场景？'

  ]

})






watch(latestRelated, (v) => emit('related-update', v), { immediate: true })

function fillQuestion(q) {
  if (!q?.trim()) return
  question.value = q.trim()
}

function snippet(msg) {

  if (msg.msg_type === 'tutoring_answer') {
    const payload = normalizeTutoringPayload(msg.payload)
    if (payload?.text_answer) {
      const t = payload.text_answer
      return t.slice(0, 80) + (t.length > 80 ? '…' : '')
    }
  }

  const t = msg.content || ''

  return t.slice(0, 80) + (t.length > 80 ? '…' : '')

}



function onTextSelect() {

  const sel = window.getSelection()

  const text = sel?.toString()?.trim()

  if (!text || !contentRef.value?.contains(sel.anchorNode)) return

  emit('selection-change', text)

}



function scrollToLatest(instant = false) {
  const apply = () => {
    const el = contentRef.value
    if (!el) return
    el.scrollTop = el.scrollHeight
  }

  if (instant) {
    nextTick(() => {
      apply()
      requestAnimationFrame(() => {
        apply()
        requestAnimationFrame(apply)
      })
    })
    return
  }

  nextTick(() => {
    const el = contentRef.value
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  })
}

async function loadSession(explicitSessionId) {

  loading.value = true

  const sid = explicitSessionId || route.query.session_id || ''

  try {

    const data = await initTutoring(studentId, sid || undefined)

    sessionId.value = data.session_id || ''

    messages.value = data.messages || []

    if (route.query.q) question.value = route.query.q

  } finally {

    loading.value = false

    scrollToLatest(Boolean(sid))

  }

}



async function startNewSession() {

  loading.value = true

  try {

    const data = await createTutoringSession(studentId)

    sessionId.value = data.session_id || ''

    messages.value = data.messages || []

    question.value = ''

    emit('selection-change', '')

    await router.replace({ path: '/chat', query: { session_id: data.session_id } })

    scrollToLatest()

    ElMessage.success('已开启新对话')

  } catch (e) {

    ElMessage.error(e.message || '开启新对话失败')

  } finally {

    loading.value = false

  }

}



async function sendQuestion() {

  const q = question.value.trim()

  if (!q) {

    ElMessage.warning('请输入问题')

    return

  }

  asking.value = true

  try {

    const payload = {

      student_id: studentId,

      question: q,

      answer_mode: answerMode.value

    }

    if (sessionId.value) payload.session_id = sessionId.value

    const ctx = { ...(context.value || {}), subject_track: subjectTrack }

    if (Object.keys(ctx).length) payload.context = ctx



    const data = await askTutoring(payload)

    if (data.session_id) sessionId.value = data.session_id

    messages.value = data.messages || []

    if (data.mastery_updates?.length) {

      try {

        await syncPathFromProfile({ studentId, subject: COURSE_NAME })

        ElMessage.info('已根据交流结果同步学习路径')

      } catch {

        /* 可选 */

      }

    }

    question.value = ''

    scrollToLatest()

  } catch (e) {

    ElMessage.error(e.message || '提问失败')

  } finally {

    asking.value = false

  }

}



function onFollowUp(action) {

  if (action.action === 'regenerate_exercise') {

    router.push({ path: '/learn/exercise-center', query: { mode: 'special', from: 'chat' } })

  } else if (action.action === 'change_difficulty' || action.action === 'view_resource') {

    router.push('/resource/personalized')

  }

}



async function onGenerateMedia(msg, idx) {

  if (!msg?.payload) return

  mediaLoadingId.value = msg.id || idx

  try {

    const data = await generateTutoringMedia({

      student_id: studentId,

      session_id: sessionId.value,

      answer: msg.payload,

      message_id: msg.id

    })

    trackBehavior(studentId, 'tutoring_media', { message_id: msg.id })

    const enriched = data.answer || data

    const i = messages.value.findIndex((m, j) => (m.id || j) === (msg.id || idx))

    if (i >= 0) {

      messages.value[i] = { ...messages.value[i], payload: enriched }

    }

    ElMessage.success('媒体已生成')

  } catch (e) {

    ElMessage.error(e.message || '媒体生成失败')

  } finally {

    mediaLoadingId.value = null

  }

}



watch(
  () => [route.path, route.query.session_id],
  ([path, sid], oldVal) => {
    if (!path.startsWith('/chat')) return
    const prevSid = oldVal?.[1]
    if (oldVal === undefined || sid !== prevSid) {
      loadSession(sid)
    }
  },
  { immediate: true }
)

watch(
  () => route.query.view,
  () => {
    if (route.path.startsWith('/chat')) scrollToLatest()
  }
)

watch(
  () => route.query.q,
  (q) => {
    if (typeof q === 'string' && q.trim()) fillQuestion(q)
  }
)

defineExpose({ fillQuestion })

</script>



<style scoped>

.agent-chat {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  padding: 20px 20px 20px 24px;
  box-sizing: border-box;
  gap: 14px;
}

.chat-top {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 4px 0;
}

.chat-heading {
  min-width: 0;
}

.panel-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--tp-text, #333338);
  letter-spacing: 0.01em;
}

.panel-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--tp-muted, #757582);
}

.new-session-btn {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--tp-border, #eeeef2);
  background: var(--tp-card, #fff);
  color: var(--tp-muted, #757582);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--tp-shadow, 0 2px 12px rgba(180, 190, 205, 0.1));
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.new-session-btn:hover {
  background: var(--tp-hover, #f4f5f8);
  color: var(--tp-text, #333338);
  border-color: var(--tp-tab-active-alt, #bde8eb);
}

.new-session-btn svg {
  width: 18px;
  height: 18px;
}

.content-card {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--tp-card, #fff);
  border-radius: var(--tp-radius-card, 16px);
  box-shadow: var(--tp-shadow, 0 2px 16px rgba(180, 190, 205, 0.12));
  border: 1px solid var(--tp-border, #eeeef2);
  padding: 24px 28px;
  line-height: 1.65;
  color: var(--tp-text, #333338);
}



.welcome-title {

  margin: 0 0 12px;

  font-size: 18px;

  font-weight: 600;

}



.welcome {

  max-width: 560px;

  margin: 24px auto;

  text-align: center;

  color: #757582;

  font-size: 14px;

}



.welcome p {

  margin: 0 0 16px;

}



.welcome-list {

  text-align: left;

  margin: 0 auto;

  padding-left: 1.2em;

  max-width: 400px;

  color: #757582;

}



.content-block {

  margin-bottom: 20px;

}



.content-block.user .user-question {
  margin: 0;
  padding: 14px 16px;
  background: var(--tp-bg, #fafafb);
  border: 1px solid var(--tp-border, #eeeef2);
  border-radius: var(--tp-radius-btn, 12px);
  font-size: 14px;
  color: var(--tp-text, #333338);
}



.system-note {

  margin: 0;

  font-size: 12px;

  color: #757582;

  padding: 8px 12px;

  border: 1px dashed #eeeef2;

  border-radius: 8px;

}



.rich-text {

  white-space: pre-wrap;

  word-break: break-word;

  font-size: 14px;

}



.history-block .section-label {

  margin: 0 0 12px;

  font-size: 13px;

  font-weight: 600;

  color: #333338;

}



.history-line {

  display: flex;

  gap: 10px;

  padding: 10px 0;

  border-bottom: 1px solid #eeeef2;

  font-size: 13px;

}



.history-role {

  flex-shrink: 0;

  width: 28px;

  color: #757582;

  font-weight: 500;

}



.history-snippet {

  color: #333338;

  line-height: 1.5;

}



.empty-hint {

  color: #757582;

  font-size: 13px;

}



.typing {

  text-align: center;

  font-size: 13px;

  color: #757582;

  padding: 12px;

}



.chat-input-bar {

  flex-shrink: 0;

  display: flex;

  flex-direction: column;

  gap: 8px;

}



.input-shell {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 14px;
  background: var(--tp-card, #fff);
  border-radius: var(--tp-radius-card, 14px);
  border: 1px solid var(--tp-border, #eeeef2);
  box-shadow: var(--tp-shadow, 0 2px 12px rgba(180, 190, 205, 0.1));
}

.round-input {
  flex: 1;
}

.round-input :deep(.el-textarea__inner) {
  border: none;
  box-shadow: none !important;
  padding: 4px 0;
  font-size: 14px;
  line-height: 1.6;
  background: transparent;
}

.send-icon-btn {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border: none;
  border-radius: var(--tp-radius-btn, 10px);
  background: var(--tp-hover, #f4f5f8);
  color: var(--tp-text, #333338);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s;
}

.send-icon-btn:hover:not(:disabled) {
  background: var(--tp-tab-active, #c7edf0);
}



.send-icon-btn:disabled {

  opacity: 0.4;

  cursor: not-allowed;

}



.send-icon-btn svg {

  width: 18px;

  height: 18px;

}



.input-meta {

  display: flex;

  align-items: center;

  gap: 10px;

  padding: 0 4px;

}



.mode-select {

  width: 120px;

}



.context-chip {

  font-size: 12px;

  color: #757582;

  padding: 2px 8px;

  background: #fff;

  border: 1px solid #eeeef2;

  border-radius: 6px;

}



.content-card :deep(.block-title) {

  color: #333338;

}



.content-card :deep(.markdown-body) {

  background: transparent;

  padding: 0;

  max-height: none;

}

</style>

