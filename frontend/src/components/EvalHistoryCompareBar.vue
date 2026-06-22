<template>
  <div class="compare-bar">
    <div class="compare-head">
      <span class="compare-title">历史报告对比</span>
      <el-button link type="primary" size="small" @click="$emit('close')">收起</el-button>
    </div>
    <div class="compare-grid">
      <div class="compare-col">
        <p class="compare-label">{{ labelA }}</p>
        <div class="compare-score">{{ reportA.overall_score }}</div>
        <p class="compare-meta">{{ formatTime(reportA.created_at) }}</p>
        <div class="mini-stages">
          <div v-for="st in stagesA" :key="st.stage" class="mini-stage">
            <span class="mini-name">{{ shortStage(st.stage_name) }}</span>
            <span class="mini-bar" :style="{ width: `${st.avg_score}%` }" />
            <span class="mini-val">{{ st.avg_score }}</span>
          </div>
        </div>
        <p class="compare-summary">{{ summaryA }}</p>
      </div>

      <div class="compare-vs">
        <span class="vs-score-delta" :class="deltaClass">
          {{ formatDelta(scoreDelta) }}
        </span>
        <span class="vs-label">综合得分变化</span>
      </div>

      <div class="compare-col">
        <p class="compare-label">{{ labelB }}</p>
        <div class="compare-score">{{ reportB.overall_score }}</div>
        <p class="compare-meta">{{ formatTime(reportB.created_at) }}</p>
        <div class="mini-stages">
          <div v-for="st in stagesB" :key="st.stage" class="mini-stage">
            <span class="mini-name">{{ shortStage(st.stage_name) }}</span>
            <span class="mini-bar" :style="{ width: `${st.avg_score}%` }" />
            <span class="mini-val">{{ st.avg_score }}</span>
          </div>
        </div>
        <p class="compare-summary">{{ summaryB }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatDelta } from '../utils/evaluationDashboard'

const props = defineProps({
  reportA: { type: Object, required: true },
  reportB: { type: Object, required: true },
  labelA: { type: String, default: '报告 A' },
  labelB: { type: String, default: '报告 B' }
})

defineEmits(['close'])

const stagesA = computed(() => props.reportA.metrics?.stage_balance || [])
const stagesB = computed(() => props.reportB.metrics?.stage_balance || [])
const summaryA = computed(
  () => props.reportA.report?.summary || props.reportA.report_summary || '—'
)
const summaryB = computed(
  () => props.reportB.report?.summary || props.reportB.report_summary || '—'
)
const scoreDelta = computed(
  () => Number(props.reportB.overall_score) - Number(props.reportA.overall_score)
)
const deltaClass = computed(() => {
  const d = scoreDelta.value
  if (d > 0) return 'delta-up'
  if (d < 0) return 'delta-down'
  return ''
})

function formatTime(iso) {
  if (!iso) return '-'
  return String(iso).replace('T', ' ').slice(0, 16)
}

function shortStage(name) {
  return String(name || '').replace(/^阶段[一二三四]·/, '')
}
</script>

<style scoped>
.compare-bar {
  background: linear-gradient(135deg, #f0f9ff 0%, #ecf5ff 100%);
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
}
.compare-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.compare-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.compare-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 16px;
  align-items: start;
}
.compare-col {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #ebeef5;
}
.compare-label {
  margin: 0 0 4px;
  font-size: 12px;
  color: #909399;
}
.compare-score {
  font-size: 28px;
  font-weight: 700;
  color: #409eff;
  line-height: 1;
}
.compare-meta {
  margin: 4px 0 8px;
  font-size: 12px;
  color: #909399;
}
.mini-stages {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}
.mini-stage {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}
.mini-name {
  width: 72px;
  color: #909399;
  flex-shrink: 0;
}
.mini-bar {
  height: 6px;
  background: #409eff;
  border-radius: 3px;
  max-width: 80px;
}
.mini-val {
  color: #606266;
  font-weight: 600;
}
.compare-summary {
  margin: 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.compare-vs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 24px;
}
.vs-score-delta {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
}
.vs-label {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}
.delta-up {
  color: #67c23a;
}
.delta-down {
  color: #e6a23c;
}
</style>
