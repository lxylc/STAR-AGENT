<template>
  <div class="path-page">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" v-loading="planning">
          <template #header>
            <div class="card-head">
              <span>个性化学习路径</span>
              <div>
                <el-button type="primary" @click="onPlan">生成路径</el-button>
                <el-button v-if="detail?.path" @click="onReplan">重新规划</el-button>
                <el-button v-if="detail?.path" @click="onRefreshPush">刷新推送</el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!detail?.path" description="请先完成画像构建（对话与练习），系统将自动评估知识点掌握度，再点击「生成路径」" />

          <template v-else>
            <el-alert
              :title="detail.path.pathName"
              :description="detail.path.pathSummary"
              :type="pathComplete ? 'success' : 'info'"
              :show-icon="pathComplete"
              :closable="false"
              class="mb"
            />
            <el-steps :active="activeStep" :finish-status="pathComplete ? 'success' : 'wait'" align-center class="mb">
              <el-step v-for="s in stageList" :key="s.no" :title="s.name" :description="`${s.items.length} 个知识点`" />
            </el-steps>
            <el-timeline>
              <el-timeline-item
                v-for="item in detail.items"
                :key="item.id"
                :type="itemStatusType(item.itemStatus)"
                :timestamp="`阶段${item.stageNo} · ${item.stageName}`"
              >
                <div class="item-row">
                  <strong>{{ item.knowledgePoint }}</strong>
                  <el-tag size="small" :type="itemStatusType(item.itemStatus)">{{ statusText(item.itemStatus) }}</el-tag>
                  <el-tag v-if="item.priority <= 2" size="small" type="danger">优先</el-tag>
                </div>
                <p class="reason">{{ item.focusReason }}</p>
                <el-button
                  v-if="item.itemStatus !== 'completed' && item.priority <= 2"
                  type="primary"
                  link
                  size="small"
                  @click.stop="goGenerateForKp(item.knowledgePoint)"
                >
                  为本知识点生成资源
                </el-button>
                <div class="progress-row">
                  <span>学习进度</span>
                  <el-slider
                    v-model="progressMap[progressKey(item)]"
                    :min="0"
                    :max="100"
                    @change="(v) => saveProgress(item, v)"
                  />
                </div>
              </el-timeline-item>
            </el-timeline>
          </template>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>推荐学习资源推送</template>
          <el-empty v-if="!pushList.length" description="暂无推送资源">
            <template #default>
              <p class="empty-hint">请先在资源中心为当前阶段知识点生成讲义/习题，再刷新推送。</p>
              <el-button type="primary" @click="goGenerateResources">去生成资源</el-button>
              <el-button v-if="detail?.path" @click="onRefreshPush">刷新推送</el-button>
            </template>
          </el-empty>
          <div v-for="row in pushList" :key="row.push.id" class="push-card" @click="openResource(row)">
            <div class="push-title">
              <el-tag size="small" :type="row.push.readStatus === 'unread' ? 'danger' : 'info'">
                {{ row.push.readStatus === 'unread' ? '未读' : '已读' }}
              </el-tag>
              {{ row.resource?.title || '资源' }}
            </div>
            <p class="push-reason">{{ row.push.pushReason }}</p>
          </div>
        </el-card>

        <el-card shadow="never" class="mt">
          <template #header>知识库（{{ graphOrder.length }} 个知识点 · 拓扑序）</template>
          <div class="graph-tags">
            <el-tag v-for="n in graphOrder" :key="n" class="kp-tag" size="small">{{ n }}</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-drawer v-model="drawer" title="推送资源" size="45%">
      <MarkdownContent v-if="currentRes" :content="currentRes.content" :show-toggle="false" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DEMO_STUDENT_ID,
  planPath,
  replanPath,
  getActivePath,
  refreshPush,
  updateProgress,
  listPush,
  markPushRead,
  getKnowledgeGraph
} from '../api/path'
import { COURSE_NAME } from '../constants/course'
import { getStudentId } from '../api/auth'
import { trackBehavior } from '../api/behavior'
import MarkdownContent from '../components/MarkdownContent.vue'

const router = useRouter()
const studentId = getStudentId() || DEMO_STUDENT_ID
const subject = COURSE_NAME
const planning = ref(false)
const detail = ref(null)
const pushList = ref([])
const graphOrder = ref([])
const progressMap = reactive({})
const drawer = ref(false)
const currentRes = ref(null)

const stageList = computed(() => {
  if (!detail.value?.items) return []
  const map = new Map()
  for (const it of detail.value.items) {
    if (!map.has(it.stageNo)) {
      map.set(it.stageNo, { no: it.stageNo, name: it.stageName, items: [] })
    }
    map.get(it.stageNo).items.push(it)
  }
  return [...map.values()].sort((a, b) => a.no - b.no)
})

const pathComplete = computed(() => {
  const items = detail.value?.items
  if (!items?.length) return false
  return items.every((i) => i.itemStatus === 'completed' || i.itemStatus === 'skipped')
})

const activeStep = computed(() => {
  const items = detail.value?.items
  if (!items?.length) return 0
  const inProg = items.find((i) => i.itemStatus === 'in_progress')
  if (inProg) return inProg.stageNo - 1
  if (pathComplete.value) return stageList.value.length
  const firstPending = items.find((i) => i.itemStatus === 'pending')
  if (firstPending) return firstPending.stageNo - 1
  return 0
})

function statusText(s) {
  return { pending: '待学', in_progress: '学习中', completed: '已完成', skipped: '跳过' }[s] || s
}
function itemStatusType(s) {
  return { pending: 'info', in_progress: 'primary', completed: 'success', skipped: 'warning' }[s] || 'info'
}

function progressKey(item) {
  return item.nodeId != null ? String(item.nodeId) : item.knowledgePoint
}

function initProgressMap() {
  for (const key of Object.keys(progressMap)) {
    delete progressMap[key]
  }
  if (detail.value?.progressList) {
    for (const p of detail.value.progressList) {
      progressMap[p.knowledgePoint] = p.progressPct
    }
  }
  if (detail.value?.items) {
    for (const it of detail.value.items) {
      const key = progressKey(it)
      if (progressMap[key] === undefined) {
        progressMap[key] = progressMap[it.knowledgePoint] ?? 0
      }
    }
  }
}

async function loadGraph() {
  const g = await getKnowledgeGraph(subject)
  graphOrder.value = g.topologicalOrder || []
}

async function loadPush() {
  pushList.value = await listPush(studentId)
}

async function loadActive() {
  detail.value = await getActivePath(studentId, subject)
  initProgressMap()
}

async function onPlan() {
  planning.value = true
  try {
    detail.value = await planPath({ studentId, subject })
    initProgressMap()
    trackBehavior(studentId, 'path_plan', { path_id: detail.value?.path?.id })
    ElMessage.success('学习路径已生成')
    await loadPush()
  } finally {
    planning.value = false
  }
}

async function onReplan() {
  if (!detail.value?.path?.id) return
  planning.value = true
  try {
    detail.value = await replanPath(detail.value.path.id)
    initProgressMap()
    ElMessage.success('路径已重新规划')
    await loadPush()
  } finally {
    planning.value = false
  }
}

async function onRefreshPush() {
  if (!detail.value?.path?.id) return
  await refreshPush(detail.value.path.id)
  ElMessage.success('已刷新推送')
  await loadActive()
  await loadPush()
}

function goGenerateResources() {
  const weak = detail.value?.items?.find((i) => i.priority <= 2 && i.itemStatus !== 'completed')
  router.push({
    path: '/resource',
    query: weak ? { kp: weak.knowledgePoint } : {}
  })
}

function goGenerateForKp(kp) {
  router.push({ path: '/resource', query: { kp } })
}

async function saveProgress(item, pct) {
  const key = progressKey(item)
  trackBehavior(studentId, 'progress_update', { knowledge_point: key, progress_pct: pct })
  await updateProgress({
    studentId,
    subject,
    knowledgePoint: key,
    progressPct: pct
  })
  await loadActive()
  await loadPush()
  if (pct >= 100) ElMessage.success(`${item.knowledgePoint} 已完成，已推进下一阶段`)
}

async function openResource(row) {
  currentRes.value = row.resource
  drawer.value = true
  if (row.push.readStatus === 'unread') {
    await markPushRead(row.push.id)
    trackBehavior(studentId, 'push_read', { push_id: row.push.id })
    await loadPush()
  }
}

onMounted(async () => {
  await loadGraph()
  await loadActive()
  await loadPush()
})
</script>

<style scoped>
.path-page { width: 100%; }
.card-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.mb { margin-bottom: 16px; }
.mt { margin-top: 16px; }
.item-row { display: flex; align-items: center; gap: 8px; }
.reason { color: #606266; font-size: 13px; margin: 6px 0; }
.progress-row { display: flex; align-items: center; gap: 12px; max-width: 400px; }
.progress-row .el-slider { flex: 1; }
.push-card {
  border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; margin-bottom: 10px;
  cursor: pointer; transition: box-shadow .2s;
}
.push-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.push-title { font-weight: 600; margin-bottom: 6px; }
.push-reason { font-size: 12px; color: #909399; margin: 0; }
.empty-hint { font-size: 13px; color: #909399; margin-bottom: 12px; }
.kp-tag { margin: 4px; }
.graph-tags { max-height: 280px; overflow-y: auto; }
.pre { white-space: pre-wrap; font-size: 14px; line-height: 1.6; }
</style>
