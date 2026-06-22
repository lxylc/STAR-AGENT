<template>
  <div ref="chartRef" class="bar-chart" :style="{ height }" />
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const emit = defineEmits(['module-click'])

const props = defineProps({
  modules: {
    type: Array,
    default: () => []
  },
  height: {
    type: String,
    default: '220px'
  },
  /** asc：分数升序（薄弱模块）；desc：分数降序（优势模块） */
  order: {
    type: String,
    default: 'asc',
    validator: (v) => v === 'asc' || v === 'desc'
  }
})

const chartRef = ref(null)
let chart = null

function buildOption() {
  const sorted = [...(props.modules || [])]
    .filter((m) => m.final_score != null)
    .sort((a, b) => {
      const diff = Number(a.final_score) - Number(b.final_score)
      return props.order === 'desc' ? -diff : diff
    })
    .slice(0, 3)

  const names = sorted.map((m) => m.module_name || '-').reverse()
  const scores = sorted.map((m) => Number(m.final_score)).reverse()

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params[0]
        if (!p) return ''
        return `${p.name}<br/>掌握分数：${p.value}`
      }
    },
    grid: {
      left: '4%',
      right: '8%',
      top: 8,
      bottom: 8,
      containLabel: true
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { type: 'dashed', color: '#e4e7ed' } },
      axisLabel: { color: '#909399' }
    },
    yAxis: {
      type: 'category',
      data: names.length ? names : ['暂无数据'],
      axisLabel: { color: '#606266', width: 120, overflow: 'truncate' },
      axisTick: { show: false },
      axisLine: { show: false }
    },
    series: [
      {
        type: 'bar',
        data: scores.length ? scores : [0],
        barMaxWidth: 28,
        itemStyle: {
          color: (params) => {
            const v = params.value
            if (v >= 70) return '#67c23a'
            if (v >= 45) return '#e6a23c'
            return '#f56c6c'
          },
          borderRadius: [0, 4, 4, 0]
        },
        label: {
          show: true,
          position: 'right',
          color: '#606266',
          formatter: '{c}'
        }
      }
    ]
  }
}

function onChartClick(params) {
  const name = params?.name
  if (!name || name === '暂无数据') return
  const mod = (props.modules || []).find((m) => m.module_name === name)
  if (mod) emit('module-click', mod)
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', onChartClick)
  }
  chart.setOption(buildOption(), true)
}

function handleResize() {
  chart?.resize()
}

watch(
  () => [props.modules, props.order],
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
.bar-chart {
  width: 100%;
  min-height: 160px;
}
</style>
