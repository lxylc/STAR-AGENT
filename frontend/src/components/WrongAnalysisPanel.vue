<template>
  <section class="wrong-analysis">
    <div class="section-head">
      <div>
        <h4 class="section-title">错题深度分析</h4>
        <p class="section-subtitle">本周期错题归因 · 画像页不提供此维度</p>
      </div>
      <el-button type="primary" size="small" @click="goWrongRedo">
        前往错题重做
      </el-button>
    </div>

    <el-empty
      v-if="!loading && analysis.total === 0"
      description="本期暂无错题记录，继续保持"
      :image-size="64"
    />

    <el-row v-else :gutter="12" v-loading="loading">
      <el-col :span="8">
        <div class="chart-card">
          <h5 class="chart-title">周期高频易错知识点 TOP5</h5>
          <div ref="kpChartRef" class="chart-box" />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="chart-card">
          <h5 class="chart-title">错误类型占比</h5>
          <div ref="typeChartRef" class="chart-box" />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="chart-card rate-card">
          <h5 class="chart-title">错题订正完成率</h5>
          <div class="rate-body">
            <el-progress
              type="circle"
              :percentage="analysis.correctionRate"
              :width="100"
              :stroke-width="8"
            />
            <p class="rate-desc">
              已复习 {{ analysis.reviewed }} / 本期错题 {{ analysis.total }} 道
            </p>
            <p class="rate-hint">基于实时错题库聚合（Mongo 已复习标记）</p>
          </div>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getWrongQuestions } from '../api/profileBuild'
import { aggregateWrongAnalysis, filterWrongByPeriod } from '../utils/evaluationDashboard'

const props = defineProps({
  studentId: { type: Number, required: true },
  periodStart: { type: String, default: null },
  periodEnd: { type: String, default: null }
})

const router = useRouter()
const loading = ref(false)
const analysis = ref({
  topKp: [],
  errorTypes: [],
  total: 0,
  reviewed: 0,
  correctionRate: 0
})

const kpChartRef = ref(null)
const typeChartRef = ref(null)
let kpChart = null
let typeChart = null

async function loadData() {
  loading.value = true
  try {
    const data = await getWrongQuestions(props.studentId, 200)
    const filtered = filterWrongByPeriod(data.items || [], props.periodStart, props.periodEnd)
    analysis.value = aggregateWrongAnalysis(filtered)
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  renderKpChart()
  renderTypeChart()
}

function renderKpChart() {
  if (!kpChartRef.value) return
  const topKp = analysis.value.topKp
  if (!topKp.length) return
  if (!kpChart) kpChart = echarts.init(kpChartRef.value)
  kpChart.setOption({
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'value', min: 0 },
    yAxis: {
      type: 'category',
      data: topKp.map((k) => k.name).reverse(),
      axisLabel: { width: 72, overflow: 'truncate' }
    },
    series: [
      {
        type: 'bar',
        data: topKp.map((k) => k.count).reverse(),
        itemStyle: { color: '#e6a23c', borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 16
      }
    ]
  })
}

function renderTypeChart() {
  if (!typeChartRef.value) return
  const types = analysis.value.errorTypes
  if (!types.length) return
  if (!typeChart) typeChart = echarts.init(typeChartRef.value)
  typeChart.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        data: types,
        label: { fontSize: 11 }
      }
    ]
  })
}

function goWrongRedo() {
  router.push({ path: '/learn/exercise-center', query: { mode: 'wrong', from: 'evaluation' } })
}

watch(
  () => [props.periodStart, props.periodEnd, props.studentId],
  () => loadData()
)

onMounted(() => loadData())

onBeforeUnmount(() => {
  kpChart?.dispose()
  typeChart?.dispose()
})
</script>

<style scoped>
.wrong-analysis {
  margin: 16px 0;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.section-title {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}
.section-subtitle {
  margin: 0;
  font-size: 12px;
  color: #909399;
}
.chart-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 10px;
  min-height: 200px;
}
.chart-title {
  margin: 0 0 8px;
  font-size: 12px;
  color: #606266;
  font-weight: 600;
}
.chart-box {
  height: 180px;
  width: 100%;
}
.rate-card .rate-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 180px;
  gap: 8px;
}
.rate-desc {
  margin: 0;
  font-size: 13px;
  color: #606266;
}
.rate-hint {
  margin: 0;
  font-size: 11px;
  color: #909399;
}
</style>
