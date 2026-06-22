<template>
  <div class="history-page">
    <el-card shadow="never" class="head-card">
      <template #header>
        <div class="card-head">
          <span>学习历史记录</span>
          <el-button link type="primary" :loading="loading" @click="load">刷新</el-button>
        </div>
      </template>
      <p class="head-desc">汇总智能辅导与画像构建对话，便于回顾学习轨迹。点击记录可继续该对话。</p>
    </el-card>

    <el-card shadow="never" v-loading="loading">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="`智能辅导 (${tutoring.length})`" name="tutoring">
          <el-empty v-if="!tutoring.length" description="暂无辅导记录" />
          <el-table
            v-else
            :data="tutoring"
            stripe
            size="small"
            class="session-table"
            @row-click="continueChat"
          >
            <el-table-column prop="updated_at" label="最近活跃" width="170">
              <template #default="{ row }">{{ formatTime(row.updated_at || row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="title" label="对话" min-width="200" show-overflow-tooltip />
            <el-table-column prop="question_count" label="问答轮数" width="90" align="center" />
            <el-table-column prop="answer" label="最近回答摘要" min-width="220" show-overflow-tooltip />
            <el-table-column label="操作" width="140" align="center">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="continueChat(row)">继续对话</el-button>
                <el-button link type="info" @click.stop="openDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`画像构建 (${profileBuild.length})`" name="build">
          <el-empty v-if="!profileBuild.length" description="暂无画像构建对话" />
          <el-timeline v-else class="build-timeline">
            <el-timeline-item
              v-for="item in profileBuild"
              :key="item.id"
              :timestamp="formatTime(item.created_at)"
              :type="item.role === 'user' ? 'primary' : 'info'"
            >
              <span class="role-tag">{{ item.role === 'user' ? '我' : 'AI' }}</span>
              {{ item.content }}
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-drawer v-model="drawerVisible" title="对话详情" size="520px">
      <div v-if="current" class="detail-block">
        <p class="detail-label">来源</p>
        <p>{{ current.source_label }}</p>
        <p class="detail-label">对话窗口</p>
        <p class="detail-text">{{ current.title || current.question }}</p>
        <p class="detail-meta">
          共 {{ current.question_count || 0 }} 轮问答 ·
          {{ formatTime(current.started_at) }} 至 {{ formatTime(current.updated_at || current.created_at) }}
        </p>

        <template v-if="current.exchanges?.length">
          <div
            v-for="(ex, idx) in current.exchanges"
            :key="ex.id || idx"
            class="exchange-item"
          >
            <p class="detail-label">第 {{ idx + 1 }} 轮 · 提问</p>
            <p class="detail-text">{{ ex.question }}</p>
            <p class="detail-label">回答</p>
            <p class="detail-text">{{ ex.answer }}</p>
            <p class="detail-meta">{{ formatTime(ex.created_at) }}</p>
          </div>
        </template>

        <template v-else>
          <p class="detail-label">提问</p>
          <p class="detail-text">{{ current.question }}</p>
          <p class="detail-label">回答</p>
          <p class="detail-text">{{ current.answer }}</p>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getLearningHistory } from '../api/profileBuild'
import { getStudentId } from '../api/auth'

const router = useRouter()

const studentId = getStudentId() || 1
const loading = ref(false)
const activeTab = ref('tutoring')
const tutoring = ref([])
const profileBuild = ref([])
const drawerVisible = ref(false)
const current = ref(null)

function formatTime(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { hour12: false })
}

function openDetail(row) {
  current.value = row
  drawerVisible.value = true
}

function continueChat(row) {
  const sid = row?.session_id
  if (!sid) {
    ElMessage.warning('无法恢复该对话')
    return
  }
  router.push({ path: '/chat', query: { session_id: sid } })
}

async function load() {
  loading.value = true
  try {
    const data = await getLearningHistory(studentId)
    tutoring.value = data.tutoring || []
    profileBuild.value = data.profile_build || []
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '加载历史失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.history-page {
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
.head-desc {
  margin: 0;
  font-size: 14px;
  color: #606266;
}
.session-table :deep(.el-table__row) {
  cursor: pointer;
}
.build-timeline {
  padding: 8px 4px 0;
}
.role-tag {
  display: inline-block;
  margin-right: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #409eff;
}
.detail-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-label {
  margin: 12px 0 0;
  font-size: 12px;
  color: #909399;
}
.detail-text {
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
}
.detail-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
.exchange-item {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
.exchange-item:first-of-type {
  margin-top: 8px;
  padding-top: 0;
  border-top: none;
}
</style>
