<template>
  <div ref="chartRef" class="stage-chart" />
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  stages: { type: Array, default: () => [] },
  height: { type: String, default: '240px' }
})

const emit = defineEmits(['stage-click'])

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value || !props.stages.length) return
  if (!chart) chart = echarts.init(chartRef.value)

  const names = props.stages.map((s) => s.stage_name)
  const scores = props.stages.map((s) => s.avg_score ?? 0)
  const overall = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0

  chart.off('click')
  chart.on('click', (params) => {
    const st = props.stages[params.dataIndex]
    if (st) emit('stage-click', st)
  })

  chart.setOption({
    grid: { left: 100, right: 24, top: 28, bottom: 28 },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const st = props.stages[p.dataIndex]
        return `${st.stage_name}<br/>本期得分：${st.avg_score} 分`
      }
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { width: 90, overflow: 'truncate' }
    },
    series: [
      {
        type: 'bar',
        data: scores.map((v, i) => ({
          value: v,
          itemStyle: {
            color: props.stages[i].is_focus ? '#f56c6c' : '#409eff',
            borderRadius: [0, 4, 4, 0]
          }
        })),
        barMaxWidth: 22,
        label: { show: true, position: 'right', formatter: '{c} 分' },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#909399', type: 'dashed' },
          data: [{ xAxis: overall, label: { formatter: `均衡线 ${overall.toFixed(0)}` } }]
        }
      }
    ]
  })
}

watch(
  () => props.stages,
  async () => {
    await nextTick()
    render()
  },
  { deep: true }
)

onMounted(async () => {
  await nextTick()
  render()
})

onBeforeUnmount(() => {
  chart?.dispose()
})
</script>

<style scoped>
.stage-chart {
  width: 100%;
  height: 240px;
}
</style>
