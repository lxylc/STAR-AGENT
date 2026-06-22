<template>

  <div ref="chartRef" class="radar-chart" :style="{ height: height }" />

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

    default: '360px'

  },

  /** score: 0~100 分；level: 1~4 等级 */

  mode: {

    type: String,

    default: 'score'

  }

})



const chartRef = ref(null)

let chart = null

/** 鼠标当前最近的雷达轴索引，供 tooltip 使用 */

let hoverDimIndex = -1



function moduleValue(mod) {

  if (props.mode === 'score') {

    const s = mod.final_score

    if (s != null && s !== '') return Number(s)

    const kps = mod.knowledge_points || []

    if (!kps.length) return 0

    const sum = kps.reduce((acc, kp) => acc + (kp.master_level || 1), 0)

    return Math.round((sum / kps.length) * 25)

  }

  const kps = mod.knowledge_points || []

  if (!kps.length) return mod.final_level || 1

  const sum = kps.reduce((acc, kp) => acc + (kp.master_level || 1), 0)

  return Math.round((sum / kps.length) * 10) / 10

}



function formatModuleTooltip(mod) {

  if (!mod) return ''

  if (props.mode === 'score') {

    return `${mod.module_name}<br/>综合分：${moduleValue(mod)}`

  }

  return `${mod.module_name}<br/>等级：L${moduleValue(mod)}`

}



function resolveDimIndex(params) {

  const p = Array.isArray(params) ? params[0] : params

  if (typeof p?.dimensionIndex === 'number' && p.dimensionIndex >= 0) {

    return p.dimensionIndex

  }

  return hoverDimIndex

}



function updateHoverDimIndex(offsetX, offsetY) {

  if (!chart) return -1

  const series = chart.getModel()?.getSeries()?.[0]

  const coordSys = series?.coordinateSystem

  if (!coordSys?.pointToData) return -1



  const dx = offsetX - coordSys.cx

  const dy = offsetY - coordSys.cy

  const dist = Math.sqrt(dx * dx + dy * dy)

  // 鼠标离雷达图太远时不显示

  if (dist > coordSys.r + 36) return -1



  const result = coordSys.pointToData([offsetX, offsetY])

  const idx = result?.[0]

  return typeof idx === 'number' && idx >= 0 ? idx : -1

}



function onZrMouseMove(e) {

  if (!chart) return

  const mods = props.modules || []

  if (!mods.length) return



  const next = updateHoverDimIndex(e.offsetX, e.offsetY)

  if (next === hoverDimIndex) return

  hoverDimIndex = next



  if (hoverDimIndex < 0) {

    chart.dispatchAction({ type: 'hideTip' })

    return

  }

  chart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: 0 })

}



function onZrGlobalOut() {

  hoverDimIndex = -1

  chart?.dispatchAction({ type: 'hideTip' })

}



function buildOption() {

  const mods = props.modules || []

  const maxVal = props.mode === 'score' ? 100 : 4

  const indicators = mods.map((m) => ({

    name: m.module_name?.length > 10 ? m.module_name.slice(0, 10) + '…' : m.module_name,

    max: maxVal

  }))

  const values = mods.map((m) => moduleValue(m))



  return {

    tooltip: {

      trigger: 'item',

      confine: true,

      formatter: (params) => {

        const modsNow = props.modules || []

        const idx = resolveDimIndex(params)

        if (idx < 0 || !modsNow[idx]) return ''

        return formatModuleTooltip(modsNow[idx])

      }

    },

    radar: {

      indicator: indicators.length ? indicators : [{ name: '暂无数据', max: maxVal }],

      radius: mods.length > 8 ? '58%' : '62%',

      splitNumber: props.mode === 'score' ? 5 : 4,

      axisName: {

        color: '#606266',

        fontSize: mods.length > 8 ? 10 : 12

      },

      splitArea: {

        areaStyle: {

          color: ['rgba(64,158,255,0.04)', 'rgba(64,158,255,0.08)']

        }

      }

    },

    series: [

      {

        type: 'radar',

        data: [

          {

            value: values.length ? values : [0],

            name: props.mode === 'score' ? '综合得分' : '掌握等级',

            symbolSize: 8,

            areaStyle: { color: 'rgba(64, 158, 255, 0.25)' },

            lineStyle: { color: '#409eff', width: 2 },

            itemStyle: { color: '#409eff' }

          }

        ]

      }

    ]

  }

}



function onChartClick(params) {

  const idx = resolveDimIndex(params)

  const mods = props.modules || []

  if (idx >= 0 && mods[idx]) {

    emit('module-click', mods[idx])

  }

}



function renderChart() {

  if (!chartRef.value) return

  if (!chart) {

    chart = echarts.init(chartRef.value)

    chart.getZr().on('mousemove', onZrMouseMove)

    chart.getZr().on('globalout', onZrGlobalOut)

    chart.on('click', onChartClick)

  }

  hoverDimIndex = -1

  chart.setOption(buildOption(), true)

}



function handleResize() {

  chart?.resize()

}



watch(

  () => [props.modules, props.mode],

  () => nextTick(renderChart),

  { deep: true }

)



onMounted(() => {

  renderChart()

  window.addEventListener('resize', handleResize)

})



onBeforeUnmount(() => {

  window.removeEventListener('resize', handleResize)

  if (chart) {

    chart.getZr().off('mousemove', onZrMouseMove)

    chart.getZr().off('globalout', onZrGlobalOut)

    chart.off('click', onChartClick)

    chart.dispose()

    chart = null

  }

})

</script>



<style scoped>

.radar-chart {

  width: 100%;

  min-height: 280px;

}

</style>


