<template>
  <div class="admin-page">
    <!-- 班级学情总览 -->
    <el-row :gutter="16" class="overview-row">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">总学生数 / 活跃人数</div>
          <div class="stat-value">
            {{ overview.total_students }}
            <span class="stat-sub">/ {{ overview.active_count }} 活跃</span>
          </div>
          <div class="stat-hint">近 7 日有学习行为视为活跃</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">班级整体平均分</div>
          <div class="stat-value" :class="scoreClass(overview.class_avg_score)">
            {{ overview.class_avg_score || '-' }}
          </div>
          <div class="stat-hint">基于各学生 12 模块画像均分汇总</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">全班 TOP3 薄弱知识点</div>
          <div v-if="overview.top3_weak_kps?.length" class="weak-kp-list">
            <div v-for="(kp, i) in overview.top3_weak_kps" :key="i" class="weak-kp-item">
              <span class="weak-kp-rank">{{ i + 1 }}</span>
              <span class="weak-kp-name">{{ kp.kp_name }}</span>
            </div>
          </div>
          <div v-else class="stat-empty">暂无薄弱知识点数据</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本周班级总做题量</div>
          <div class="stat-value">{{ overview.weekly_question_count }}</div>
          <div class="stat-hint">自然周（周一至周日）答题记录汇总</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 学生列表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="head">
          <span class="page-title">学生管理</span>
          <div class="head-actions">
            <el-button type="primary" plain :disabled="!filteredStudents.length" @click="exportAll">
              导出全班学情 Excel 报表
            </el-button>
          </div>
        </div>
        <div class="filter-bar">
          <el-input
            v-model="keyword"
            placeholder="搜索用户名/姓名"
            style="width:220px"
            clearable
            @change="load"
          />
          <el-select v-model="gradeFilter" placeholder="年级筛选" clearable style="width:130px" @change="load">
            <el-option v-for="g in gradeOptions" :key="g" :label="g" :value="g" />
          </el-select>
          <el-select v-model="scoreFilter" placeholder="分数区间" clearable style="width:140px" @change="applyFilters">
            <el-option label="优秀 (≥70)" value="high" />
            <el-option label="中等 (45-69)" value="mid" />
            <el-option label="薄弱 (<45)" value="low" />
            <el-option label="暂无画像" value="none" />
          </el-select>
          <el-select v-model="activityFilter" placeholder="活跃度" clearable style="width:130px" @change="applyFilters">
            <el-option label="近7日活跃" value="active" />
            <el-option label="7日未活跃" value="inactive" />
          </el-select>
        </div>
        <div v-if="selectedIds.length" class="batch-bar">
          <span>已选 {{ selectedIds.length }} 人</span>
          <el-button size="small" type="primary" plain @click="exportSelected">批量导出</el-button>
          <el-button size="small" type="warning" plain @click="confirmBatchReset">批量重置密码</el-button>
        </div>
      </template>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredStudents"
        border
        row-key="id"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="100" />
        <el-table-column prop="realName" label="姓名" min-width="90" />
        <el-table-column prop="grade" label="年级" width="90" />
        <el-table-column prop="major" label="专业" min-width="120" show-overflow-tooltip />
        <el-table-column label="整体学情均分" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.avgScore != null" :class="scoreClass(row.avgScore)">{{ row.avgScore }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="最近活跃时间" width="160">
          <template #default="{ row }">
            <span v-if="row.lastActiveAt">{{ row.lastActiveAt }}</span>
            <span v-else class="text-muted">暂无记录</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled !== false ? 'success' : 'danger'" size="small">
              {{ row.enabled !== false ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewProfile(row.id)">画像</el-button>
            <el-button link type="primary" @click="viewEvaluation(row.id)">查看评估</el-button>
            <el-button link type="warning" @click="confirmReset(row)">重置密码</el-button>
            <el-button
              link
              :type="row.enabled !== false ? 'danger' : 'success'"
              @click="confirmToggleStatus(row)"
            >
              {{ row.enabled !== false ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 全班知识点掌握度条形图 -->
    <el-card shadow="never" class="chart-card">
      <ClassModuleBarChart :modules="overview.module_scores || []" height="380px" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listStudents } from '../../api/auth'
import {
  getClassOverview,
  getStudentsStats,
  resetStudentPassword,
  batchResetPassword,
  setStudentStatus,
  exportStudentsCsv
} from '../../api/admin'
import ClassModuleBarChart from '../../components/ClassModuleBarChart.vue'

const router = useRouter()
const loading = ref(false)
const students = ref([])
const overview = ref({
  total_students: 0,
  active_count: 0,
  class_avg_score: 0,
  top3_weak_kps: [],
  weekly_question_count: 0,
  module_scores: []
})
const keyword = ref('')
const gradeFilter = ref('')
const scoreFilter = ref('')
const activityFilter = ref('')
const selectedIds = ref([])
const tableRef = ref(null)

const gradeOptions = ['大一', '大二', '大三', '大四', '研一', '研二']

const filteredStudents = computed(() => {
  let list = [...students.value]
  if (scoreFilter.value) {
    list = list.filter((s) => {
      const score = s.avgScore
      if (scoreFilter.value === 'none') return score == null || score === 0
      if (score == null) return false
      if (scoreFilter.value === 'high') return score >= 70
      if (scoreFilter.value === 'mid') return score >= 45 && score < 70
      if (scoreFilter.value === 'low') return score < 45
      return true
    })
  }
  if (activityFilter.value) {
    const now = Date.now()
    const weekMs = 7 * 24 * 3600 * 1000
    list = list.filter((s) => {
      if (!s.lastActiveAt) return activityFilter.value === 'inactive'
      const t = new Date(s.lastActiveAt.replace(' ', 'T')).getTime()
      const active = now - t <= weekMs
      return activityFilter.value === 'active' ? active : !active
    })
  }
  return list
})

function scoreClass(score) {
  if (score == null) return ''
  if (score >= 70) return 'score-high'
  if (score >= 45) return 'score-mid'
  return 'score-low'
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

function applyFilters() {
  /* 前端筛选，无需重新请求 */
}

async function loadOverview(ids) {
  try {
    overview.value = await getClassOverview(ids)
  } catch {
    overview.value = {
      total_students: ids.length,
      active_count: 0,
      class_avg_score: 0,
      top3_weak_kps: [],
      weekly_question_count: 0,
      module_scores: []
    }
  }
}

async function load() {
  loading.value = true
  try {
    const raw = await listStudents({
      keyword: keyword.value || undefined,
      grade: gradeFilter.value || undefined
    })
    const ids = raw.map((s) => s.id)
    let statsMap = {}
    if (ids.length) {
      try {
        const statsRes = await getStudentsStats(ids)
        statsMap = statsRes.students || {}
      } catch {
        /* Flask 未启动时仍展示基础列表 */
      }
    }
    students.value = raw.map((s) => {
      const st = statsMap[s.id] || {}
      return {
        ...s,
        enabled: s.enabled !== false && s.enabled !== 0,
        avgScore: st.avg_score ?? null,
        lastActiveAt: st.last_active_at ?? null
      }
    })
    await loadOverview(ids)
  } finally {
    loading.value = false
  }
}

function openInNewTab(path, studentId) {
  const route = router.resolve({ path, query: { studentId } })
  window.open(route.href, '_blank')
}

function viewProfile(id) {
  openInNewTab('/profile/view', id)
}

function viewEvaluation(id) {
  openInNewTab('/evaluation', id)
}

async function confirmReset(row) {
  try {
    await ElMessageBox.confirm(
      `确定将学生「${row.realName || row.username}」的密码重置为默认密码 123456 吗？`,
      '重置密码',
      { type: 'warning', confirmButtonText: '确认重置', cancelButtonText: '取消' }
    )
    await resetStudentPassword(row.id)
    ElMessage.success('密码已重置为 123456')
  } catch (e) {
    if (e !== 'cancel' && !e?.message?.includes('系统繁忙') && !e?.message?.includes('请求失败')) {
      ElMessage.error('重置失败')
    }
  }
}

async function confirmBatchReset() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${selectedIds.value.length} 名学生密码重置为默认密码 123456 吗？`,
      '批量重置密码',
      { type: 'warning', confirmButtonText: '确认重置', cancelButtonText: '取消' }
    )
    await batchResetPassword(selectedIds.value)
    ElMessage.success(`已成功重置 ${selectedIds.value.length} 名学生密码`)
  } catch (e) {
    if (e !== 'cancel' && !e?.message?.includes('系统繁忙') && !e?.message?.includes('请求失败')) {
      ElMessage.error('批量重置失败')
    }
  }
}

async function confirmToggleStatus(row) {
  const enabling = row.enabled === false
  const action = enabling ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(
      `确定${action}学生「${row.realName || row.username}」的账号吗？${enabling ? '' : '禁用后该学生将无法登录。'}`,
      `${action}账号`,
      { type: 'warning', confirmButtonText: `确认${action}`, cancelButtonText: '取消' }
    )
    await setStudentStatus(row.id, enabling)
    row.enabled = enabling
    ElMessage.success(`账号已${action}`)
  } catch (e) {
    if (e !== 'cancel' && !e?.message?.includes('系统繁忙') && !e?.message?.includes('请求失败')) {
      ElMessage.error(`${action}失败`)
    }
  }
}

function exportAll() {
  exportStudentsCsv(filteredStudents.value, '全班学情报表.csv')
  ElMessage.success('报表已导出')
}

function exportSelected() {
  const rows = students.value.filter((s) => selectedIds.value.includes(s.id))
  exportStudentsCsv(rows, `选中学生学情_${selectedIds.value.length}人.csv`)
  ElMessage.success('选中学生报表已导出')
}

onMounted(load)
</script>

<style scoped>
.admin-page {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview-row {
  margin-bottom: 0;
}

.stat-card {
  height: 120px;
}

.stat-card :deep(.el-card__body) {
  padding: 16px 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.stat-sub {
  font-size: 16px;
  font-weight: 400;
  color: #606266;
}

.stat-hint {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 6px;
}

.stat-empty {
  font-size: 13px;
  color: #c0c4cc;
}

.weak-kp-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.weak-kp-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.weak-kp-rank {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fef0f0;
  color: #f56c6c;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.weak-kp-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-card :deep(.el-card__header) {
  padding-bottom: 12px;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  padding: 8px 12px;
  background: #ecf5ff;
  border-radius: 6px;
  font-size: 13px;
  color: #409eff;
}

.chart-card {
  margin-bottom: 8px;
}

.score-high { color: #67c23a; font-weight: 600; }
.score-mid { color: #e6a23c; font-weight: 600; }
.score-low { color: #f56c6c; font-weight: 600; }
.text-muted { color: #c0c4cc; font-size: 13px; }
</style>
