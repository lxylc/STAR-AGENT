<template>
  <div class="resource-page">
    <el-row :gutter="16">
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>多智能体资源生成 · Python程序设计</template>
          <el-form :model="form" label-width="100px">
            <el-form-item label="生成模式">
              <el-radio-group v-model="form.batch">
                <el-radio :value="false">单个知识点</el-radio>
                <el-radio :value="true">批量知识点</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="!form.batch" label="知识点">
              <el-input v-model="form.knowledgePoint" placeholder="如：变量与数据类型" />
            </el-form-item>
            <el-form-item v-else label="知识点列表">
              <el-input
                v-model="batchText"
                type="textarea"
                :rows="4"
                placeholder="每行一个知识点&#10;变量与数据类型&#10;控制流程&#10;函数"
              />
            </el-form-item>
            <el-form-item label="智能体">
              <el-checkbox-group v-model="form.agentTypes">
                <el-checkbox label="LECTURE">讲义梳理</el-checkbox>
                <el-checkbox label="EXERCISE">习题生成</el-checkbox>
                <el-checkbox label="COURSEWARE">课件编辑</el-checkbox>
              </el-checkbox-group>
              <div class="hint">不选则默认执行全部；习题/课件会自动先跑讲义智能体</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="generating" @click="onGenerate">
                启动智能体集群生成
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="generating"
            title="智能体集群执行中…"
            type="info"
            :closable="false"
            show-icon
            class="task-alert"
          />
          <el-steps v-if="subTasks.length" :active="subTaskActive" finish-status="success" align-center class="task-steps">
            <el-step
              v-for="st in subTasks"
              :key="st.id"
              :title="agentLabel(st.agentType)"
              :description="subTaskDesc(st)"
              :status="subTaskStepStatus(st)"
            />
          </el-steps>
          <el-alert
            v-if="lastTask && !generating"
            :title="`最近任务 #${lastTask.task.id} - ${lastTask.task.taskStatus}`"
            :type="taskAlertType"
            :closable="false"
            show-icon
            class="task-alert"
          />
          <el-button
            v-if="failedAgentTypes.length"
            type="warning"
            size="small"
            class="retry-btn"
            :loading="generating"
            @click="retryFailed"
          >
            重试失败子任务（{{ failedAgentTypes.join('、') }}）
          </el-button>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-head">
              <span>学习资源库</span>
              <el-button link type="primary" @click="loadResources">刷新</el-button>
            </div>
          </template>
          <el-form :inline="true" class="filter">
            <el-form-item label="类型">
              <el-select v-model="filter.resourceType" clearable placeholder="全部" style="width:140px">
                <el-option label="讲义" value="lecture" />
                <el-option label="习题" value="exercise" />
                <el-option label="课件" value="courseware" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button @click="loadResources">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="resources" v-loading="loading" stripe @row-click="openDetail">
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="resourceType" label="类型" width="90">
              <template #default="{ row }">{{ typeLabel(row.resourceType) }}</template>
            </el-table-column>
            <el-table-column prop="knowledgePoint" label="知识点" width="120" show-overflow-tooltip />
            <el-table-column prop="createdAt" label="创建时间" width="170" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <ResourceDetailDrawer v-model:visible="drawerVisible" :resource="current" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ResourceDetailDrawer from '../components/ResourceDetailDrawer.vue'
import { DEMO_STUDENT_ID, generateResource, listResources } from '../api/resource'
import { getStudentId } from '../api/auth'
import { trackBehavior } from '../api/behavior'
import { COURSE_NAME } from '../constants/course'

const route = useRoute()
const studentId = getStudentId() || DEMO_STUDENT_ID
const generating = ref(false)
const loading = ref(false)
const resources = ref([])
const lastTask = ref(null)
const subTasks = ref([])
const drawerVisible = ref(false)
const current = ref(null)
const batchText = ref('')

const form = reactive({
  batch: false,
  knowledgePoint: '变量与数据类型',
  agentTypes: []
})

const filter = reactive({ resourceType: '' })

const taskAlertType = computed(() => {
  const s = lastTask.value?.task?.taskStatus
  return { SUCCESS: 'success', PARTIAL: 'warning', FAILED: 'error' }[s] || 'info'
})

const subTaskActive = computed(() => {
  const idx = subTasks.value.findIndex((s) => s.subStatus === 'RUNNING')
  if (idx >= 0) return idx
  const done = subTasks.value.filter((s) => s.subStatus === 'SUCCESS').length
  return done
})

const failedAgentTypes = computed(() =>
  (subTasks.value || [])
    .filter((s) => s.subStatus === 'FAILED')
    .map((s) => s.agentType)
    .filter(Boolean)
)

function agentLabel(t) {
  return { LECTURE: '讲义', EXERCISE: '习题', COURSEWARE: '课件' }[t] || t
}

function subTaskDesc(st) {
  return st.subStatus || 'PENDING'
}

function subTaskStepStatus(st) {
  if (st.subStatus === 'SUCCESS') return 'success'
  if (st.subStatus === 'FAILED') return 'error'
  if (st.subStatus === 'RUNNING') return 'process'
  return 'wait'
}

function typeLabel(t) {
  return { lecture: '讲义', exercise: '习题', courseware: '课件', exam_summary: '考点' }[t] || t
}

async function onGenerate() {
  const payload = {
    studentId,
    subject: COURSE_NAME,
    batch: form.batch,
    agentTypes: form.agentTypes.length ? form.agentTypes : undefined
  }
  if (form.batch) {
    const points = batchText.value.split('\n').map((s) => s.trim()).filter(Boolean)
    if (!points.length) {
      ElMessage.warning('请填写批量知识点，每行一个')
      return
    }
    payload.knowledgePoints = points
  } else {
    if (!form.knowledgePoint?.trim()) {
      ElMessage.warning('请填写知识点')
      return
    }
    payload.knowledgePoint = form.knowledgePoint.trim()
  }

  generating.value = true
  subTasks.value = (payload.agentTypes || ['LECTURE', 'EXERCISE', 'COURSEWARE']).map((t, i) => ({
    id: i,
    agentType: t,
    subStatus: 'RUNNING'
  }))
  try {
    lastTask.value = await generateResource(payload)
    subTasks.value = lastTask.value?.subTasks || []
    trackBehavior(studentId, 'resource_generate', {
      task_id: lastTask.value?.task?.id,
      status: lastTask.value?.task?.taskStatus
    })
    ElMessage.success('资源生成完成')
    await loadResources()
  } finally {
    generating.value = false
    if (lastTask.value?.subTasks) subTasks.value = lastTask.value.subTasks
  }
}

async function retryFailed() {
  if (!failedAgentTypes.value.length) return
  form.agentTypes = [...failedAgentTypes.value]
  await onGenerate()
}

async function loadResources() {
  loading.value = true
  try {
    resources.value = await listResources({
      studentId,
      subject: COURSE_NAME,
      resourceType: filter.resourceType || undefined
    })
  } finally {
    loading.value = false
  }
}

function openDetail(row) {
  current.value = row
  drawerVisible.value = true
  trackBehavior(studentId, 'resource_view', { resource_id: row.id, type: row.resourceType })
}

onMounted(() => {
  if (route.query.kp) form.knowledgePoint = String(route.query.kp)
  loadResources()
})
</script>

<style scoped>
.resource-page { width: 100%; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.hint { font-size: 12px; color: #909399; margin-top: 4px; }
.task-alert { margin-top: 12px; }
.task-steps { margin-top: 12px; }
.retry-btn { margin-top: 8px; }
.filter { margin-bottom: 8px; }
</style>
