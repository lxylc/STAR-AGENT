<template>
  <el-drawer :model-value="visible" :title="title" size="58%" @update:model-value="$emit('update:visible', $event)">
    <div v-if="resource" class="detail-body">
      <div class="detail-tags">
        <el-tag>{{ typeLabel(resource.resourceType) }}</el-tag>
        <el-tag v-if="resource.preview" type="info" size="small">系统推荐</el-tag>
        <el-tag v-if="isCourseware" type="success" size="small" effect="plain">观看学习</el-tag>
      </div>
      <h3 class="detail-title">{{ resource.title }}</h3>
      <p v-if="resource.knowledgePoint" class="detail-kp">知识点：{{ resource.knowledgePoint }}</p>

      <ExerciseStructured
        v-if="resource.resourceType === 'exercise' && exerciseJson"
        :content-json="exerciseJson"
      />

      <!-- 代码案例：分段渲染（正文 + 代码 + 正文），避免 Markdown 解析错乱 -->
      <template v-else-if="isCourseware">
        <MarkdownContent v-if="showcase.before" :content="showcase.before" :show-toggle="false" />
        <div v-if="showcase.code" class="code-readonly">
          <div class="code-readonly-label">{{ showcase.language || 'python' }}</div>
          <pre class="code-readonly-body"><code>{{ showcase.code }}</code></pre>
        </div>
        <MarkdownContent v-if="showcase.after" :content="showcase.after" :show-toggle="false" />
        <div v-if="showcase.code" class="code-showcase-actions">
          <el-button type="primary" plain :loading="demoRunning" @click="runDemo">运行演示</el-button>
          <el-button plain @click="copyCode">复制代码</el-button>
        </div>
        <el-alert
          v-if="demoResult"
          :title="demoResult.ok ? '演示运行成功' : '演示运行失败'"
          :type="demoResult.ok ? 'success' : 'error'"
          :description="demoResult.ok ? demoResult.output : demoResult.error"
          :closable="false"
          show-icon
          class="demo-alert"
        />
      </template>

      <!-- 讲义：排版阅读 -->
      <MarkdownContent
        v-else-if="isLecture"
        :content="resource.content"
        :show-toggle="false"
      />

      <!-- 习题预览 / 其他 -->
      <MarkdownContent
        v-else-if="resource.resourceType === 'exercise' || resource.content"
        :content="resource.content"
        :show-toggle="false"
      />

      <div class="detail-actions">
        <el-button
          v-if="resource.resourceType === 'exercise'"
          type="primary"
          :disabled="isCompleted || needsGenerate"
          @click="goExercise"
        >
          {{ needsGenerate ? '请先一键生成' : isCompleted ? '已完成 ✓' : '前往习题中心作答' }}
        </el-button>
        <el-button type="primary" plain @click="goTutoring">针对本资源提问</el-button>
        <el-button v-if="hasCodeBlock && !isCourseware" type="primary" plain @click="copyCode">
          复制代码
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import MarkdownContent from './MarkdownContent.vue'
import ExerciseStructured from './ExerciseStructured.vue'
import { extractCodeBlock, splitMarkdownCodeSections } from '../utils/markdown'
import { runPythonCode } from '../api/profileBuild'
import { trackBehavior } from '../api/behavior'

const router = useRouter()

const props = defineProps({
  visible: Boolean,
  resource: { type: Object, default: null },
  title: { type: String, default: '资源详情' },
  studentId: { type: Number, default: 1 },
  statusMap: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:visible', 'status-change'])

const demoRunning = ref(false)
const demoResult = ref(null)

const resourceStatus = computed(() => {
  const id = props.resource?.id
  return id ? props.statusMap[String(id)] : null
})
const isCompleted = computed(() => resourceStatus.value?.status === 'completed')
const exerciseJson = computed(() => props.resource?.contentJson || props.resource?.content_json || '')
const needsGenerate = computed(
  () =>
    props.resource?.resourceType === 'exercise' &&
    (props.resource?.preview || props.resource?.pending_generate || !exerciseJson.value)
)

const TYPE_LABELS = {
  lecture: '讲义',
  exercise: '习题',
  courseware: '代码案例',
  exam_summary: '考点'
}

function typeLabel(t) {
  return TYPE_LABELS[t] || t
}

const isLecture = computed(
  () => props.resource?.resourceType === 'lecture' || props.resource?.resourceType === 'exam_summary'
)
const isCourseware = computed(() => props.resource?.resourceType === 'courseware')
const showcase = computed(() => splitMarkdownCodeSections(props.resource?.content || ''))
const codeSnippet = computed(() => showcase.value.code || extractCodeBlock(props.resource?.content || ''))
const hasCodeBlock = computed(() => props.resource?.content?.includes('```'))

watch(
  () => props.visible,
  (v) => {
    if (v && props.resource) {
      trackBehavior(props.studentId, 'resource_view', {
        resource_id: props.resource.id,
        resource_type: props.resource.resourceType,
        module_id: props.resource.module_id
      })
    }
  }
)

watch(
  () => props.resource,
  () => {
    demoResult.value = null
  }
)

function copyCode() {
  const code = extractCodeBlock(props.resource?.content)
  navigator.clipboard.writeText(code).then(
    () => ElMessage.success('已复制到剪贴板'),
    () => ElMessage.error('复制失败')
  )
}

async function runDemo() {
  demoRunning.value = true
  demoResult.value = null
  try {
    demoResult.value = await runPythonCode({
      student_id: props.studentId,
      code: codeSnippet.value,
      resource_id: props.resource?.id
    })
    trackBehavior(props.studentId, 'code_showcase', {
      action: 'demo_run',
      resource_id: props.resource?.id,
      module_id: props.resource?.module_id,
      ok: demoResult.value?.ok
    })
  } catch (e) {
    demoResult.value = { ok: false, error: e?.response?.data?.error || '演示运行失败' }
  } finally {
    demoRunning.value = false
  }
}

function goExercise() {
  const r = props.resource
  if (!r || isCompleted.value) return
  if (r.preview || r.pending_generate || !r.contentJson) {
    ElMessage.warning('请先点击「星火 AI 深度生成」，生成针对薄弱点的专项习题')
    return
  }
  router.push({
    path: '/learn/exercise-center',
    query: {
      studentId: props.studentId,
      mode: 'special',
      from: 'resource'
    }
  })
  emit('update:visible', false)
}

function goTutoring() {
  const r = props.resource
  if (!r) return
  router.push({
    path: '/chat',
    query: {
      kp: r.knowledgePoint || '',
      title: r.title || '',
      excerpt: (r.content || '').slice(0, 500)
    }
  })
}
</script>

<style scoped>
.detail-body {
  padding: 0 4px;
}
.detail-tags {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.detail-title {
  margin: 12px 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.detail-kp {
  margin: 0 0 8px;
  font-size: 13px;
  color: #909399;
}
.code-showcase-actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.code-readonly {
  margin: 12px 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #2c313a;
}
.code-readonly-label {
  padding: 6px 12px;
  font-size: 12px;
  color: #abb2bf;
  background: #21252b;
  border-bottom: 1px solid #2c313a;
  text-transform: lowercase;
}
.code-readonly-body {
  margin: 0;
  padding: 14px 16px;
  background: #282c34;
  color: #abb2bf;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
}
.code-readonly-body code {
  font-family: inherit;
}
.demo-alert {
  margin-top: 10px;
}
.detail-actions {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
