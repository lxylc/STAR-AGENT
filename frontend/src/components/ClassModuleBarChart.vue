<template>
  <div ref="chartRef" class="class-module-chart" :style="{ height }" />
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  modules: {
    type: Array,
    default: () => []
  },
  height: {
    type: String,
    default: '360px'
  }
})

const chartRef = ref(null)
let chart = null

function buildOption() {
  const items = [...(props.modules || [])].sort((a, b) => a.module_id - b.module_id)
  const names = items.map((m) => m.module_name || '-')
  const scores = items.map((m) => Number(m.avg_score ?? 0))

  return {
    title: {
      text: '全班知识点整体掌握度',
      left: 'center',
      top: 0,
      textStyle: { fontSize: 14, fontWeight: 600, color: '#303133' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params[0]
        if (!p) return ''
        const mod = items[p.dataIndex]
        return `${p.name}<br/>班级均分：${p.value}<br/>有数据学生：${mod?.student_count ?? 0} 人`
      }
    },
    grid: {
      left: '3%',
      right: '6%',
      top: 40,
      bottom: 24,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: names.length ? names : ['暂无数据'],
      axisLabel: {
        color: '#606266',
        rotate: names.length > 6 ? 30 : 0,
        interval: 0,
        fontSize: 11
      },
      axisTick: { alignWithLabel: true }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      name: '均分',
      splitLine: { lineStyle: { type: 'dashed', color: '#e4e7ed' } },
      axisLabel: { color: '#909399' }
    },
    series: [
      {
        type: 'bar',
        data: scores.length ? scores : [0],
        barMaxWidth: 36,
        itemStyle: {
          color: (params) => {
            const v = params.value
            if (v >= 70) return '#67c23a'
            if (v >= 45) return '#e6a23c'
            return '#f56c6c'
          },
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true,
          position: 'top',
          color: '#606266',
          fontSize: 11,
          formatter: '{c}'
        }
      }
    ]
  }
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
  () => props.modules,
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
.class-module-chart {
  width: 100%;
  min-height: 280px;
}
</style>
