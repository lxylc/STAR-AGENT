<template>
  <div ref="chartRef" class="line-chart" :style="{ height }" />
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  points: {
    type: Array,
    default: () => []
  },
  height: {
    type: String,
    default: '280px'
  }
})

const chartRef = ref(null)
let chart = null

function buildOption() {
  const pts = props.points || []
  const dates = pts.map((p) => p.date)
  const scores = pts.map((p) => p.score)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        if (!p) return ''
        const pt = pts[p.dataIndex]
        return `${pt?.fullDate ? formatFull(pt.fullDate) : p.name}<br/>平均分：${p.value}`
      }
    },
    grid: {
      left: '4%',
      right: '4%',
      top: 32,
      bottom: 8,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLabel: { color: '#909399' },
      axisLine: { lineStyle: { color: '#dcdfe6' } }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { type: 'dashed', color: '#e4e7ed' } },
      axisLabel: { color: '#909399' }
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: scores,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff', borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64,158,255,0.25)' },
              { offset: 1, color: 'rgba(64,158,255,0.02)' }
            ]
          }
        },
        label: {
          show: true,
          position: 'top',
          color: '#409eff',
          fontWeight: 600,
          formatter: '{c}'
        }
      }
    ]
  }
}

function formatFull(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(buildOption(), true)
}

function handleResize() {
  chart?.resize()
}

watch(
  () => props.points,
  () => nextTick(renderChart),
  { deep: true }
)

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.line-chart {
  width: 100%;
  min-height: 200px;
}
</style>
