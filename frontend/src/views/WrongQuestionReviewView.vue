<template>
  <div class="wrong-page">
    <ProfileRequiredAlert :loading="profileLoading" :profile-completed="profileCompleted" />

    <el-card shadow="never" class="head-card">
      <template #header>
        <div class="card-head">
          <span>错题复习</span>
          <div class="head-actions">
            <el-button link type="primary" :loading="loading" @click="load">刷新</el-button>
            <el-button
              :disabled="!profileCompleted || !items.length"
              @click="toggleSelectAll"
            >
              {{ allSelected ? '取消全选' : '全选错题' }}
            </el-button>
            <el-button
              type="primary"
              :disabled="!profileCompleted || !selectedIds.length"
              @click="redoSelected"
            >
              批量重做 ({{ selectedIds.length }})
            </el-button>
            <el-button type="primary" plain :disabled="!profileCompleted" @click="goPractice">
              去习题中心
            </el-button>
          </div>
        </div>
      </template>
      <p class="head-desc">
        汇总画像测评与模块练习中的错题，支持单道/批量重做；做对自动移出错题本并更新画像。
      </p>
      <div v-if="moduleStats.length" class="stats-row">
        <el-tag
          v-for="m in moduleStats"
          :key="m.module_id"
          type="danger"
          effect="plain"
          class="stat-tag"
          @click="goModulePractice(m.module_id)"
        >
          {{ m.module_name }} · {{ m.wrong_count }} 题 →
        </el-tag>
      </div>
    </el-card>

    <el-card shadow="never" v-loading="loading || profileLoading">
      <el-empty
        v-if="profileCompleted && !items.length"
        description="暂无错题，继续保持！"
      />
      <el-empty
        v-else-if="!profileCompleted"
        description="请先完成画像构建"
      />

      <div v-else class="wrong-list">
        <div v-for="item in items" :key="item.id" class="wrong-card">
          <div class="wrong-head">
            <el-checkbox
              :model-value="selectedIds.includes(item.id)"
              @change="(v) => toggleSelect(item.id, v)"
            />
            <el-tag size="small" type="info">{{ item.source_label }}</el-tag>
            <el-tag v-if="item.module_name" size="small">{{ item.module_name }}</el-tag>
            <el-tag v-if="item.kp_name" size="small" type="warning">{{ item.kp_name }}</el-tag>
            <el-tag v-if="item.reviewed" size="small" type="success">已复习</el-tag>
            <span class="wrong-time">{{ formatTime(item.created_at) }}</span>
          </div>
          <p class="wrong-content">{{ item.content }}</p>
          <div class="answer-grid">
            <div>
              <span class="label wrong-label">你的答案</span>
              <p>{{ item.user_answer || '—' }}</p>
            </div>
            <div>
              <span class="label correct-label">正确答案</span>
              <p>{{ item.correct_answer || '—' }}</p>
            </div>
          </div>
          <p v-if="item.analysis" class="analysis">解析：{{ item.analysis }}</p>
          <p v-if="item.judge_reason" class="analysis">判题说明：{{ item.judge_reason }}</p>
          <div class="card-actions">
            <el-button size="small" type="primary" @click="redoOne(item)">
              重做此题
            </el-button>
            <el-button
              v-if="!item.reviewed && !String(item.id).startsWith('quiz-')"
              size="small"
              @click="markReviewed(item)"
            >
              标记已复习
            </el-button>
            <el-button
              v-if="item.module_id"
              size="small"
              type="primary"
              link
              @click="goModulePractice(item.module_id)"
            >
              专项练习 →
            </el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ProfileRequiredAlert from '../components/ProfileRequiredAlert.vue'
import { useRequiresProfile } from '../composables/useRequiresProfile'
import { getWrongQuestions, markWrongReviewed } from '../api/profileBuild'
import { getStudentId } from '../api/auth'

const router = useRouter()
const studentId = getStudentId() || 1
const { loading: profileLoading, profileCompleted } = useRequiresProfile()

const loading = ref(false)
const items = ref([])
const moduleStats = ref([])
const selectedIds = ref([])

const allSelected = computed(
  () => items.value.length > 0 && selectedIds.value.length === items.value.length
)

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = items.value.map((item) => item.id)
  }
}

function formatTime(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  if (!profileCompleted.value) return
  loading.value = true
  selectedIds.value = []
  try {
    const data = await getWrongQuestions(studentId)
    items.value = data.items || []
    moduleStats.value = data.module_stats || []
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '加载错题失败')
  } finally {
    loading.value = false
  }
}

function toggleSelect(id, checked) {
  if (checked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  }
}

async function markReviewed(item) {
  try {
    await markWrongReviewed({ student_id: studentId, item_id: item.id })
    item.reviewed = true
    ElMessage.success('已标记为已复习')
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '操作失败')
  }
}

function goPractice() {
  router.push({
    path: '/learn/exercise-center',
    query: { mode: 'wrong', from: 'wrong_review' }
  })
}

function redoOne(item) {
  router.push({
    path: '/learn/exercise-center',
    query: {
      mode: 'wrong',
      itemIds: item.id,
      from: 'wrong_review'
    }
  })
}

function redoSelected() {
  if (!selectedIds.value.length) return
  router.push({
    path: '/learn/exercise-center',
    query: {
      mode: 'wrong',
      itemIds: selectedIds.value.join(','),
      from: 'wrong_review'
    }
  })
}

function goModulePractice(moduleId) {
  router.push({
    path: '/learn/exercise-center',
    query: {
      studentId,
      moduleId,
      mode: 'special',
      from: 'wrong_review'
    }
  })
}

onMounted(() => {
  if (profileCompleted.value) load()
})

onActivated(() => {
  if (profileCompleted.value) load()
})

watch(profileCompleted, (completed) => {
  if (completed) load()
})
</script>

<style scoped>
.wrong-page {
  width: 100%;
  margin: 0 auto;
  padding-bottom: 32px;
}
.head-card {
  margin-bottom: 16px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.head-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.head-desc {
  margin: 0 0 12px;
  font-size: 14px;
  color: #606266;
}
.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.stat-tag {
  cursor: pointer;
}
.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.wrong-card {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafafa;
}
.wrong-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.wrong-time {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}
.wrong-content {
  margin: 0 0 12px;
  font-size: 15px;
  line-height: 1.7;
  color: #303133;
}
.answer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 8px;
}
.label {
  font-size: 12px;
  font-weight: 600;
}
.wrong-label {
  color: #f56c6c;
}
.correct-label {
  color: #67c23a;
}
.answer-grid p {
  margin: 4px 0 0;
  font-size: 14px;
}
.analysis {
  margin: 8px 0 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
.card-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
