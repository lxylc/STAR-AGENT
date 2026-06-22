import { LEARNING_STAGES, MODULE_NAMES } from '../constants/modules'

/** 错题错误类型归类 */
export function categorizeErrorType(item) {
  const reason = String(item.judge_reason || item.analysis || '').toLowerCase()
  const qtype = item.qtype || item.type || 'choice'
  if (reason.includes('粗心') || reason.includes('看错') || reason.includes('漏')) return '粗心失误'
  if (qtype === 'coding') return '编程实操薄弱'
  if (qtype === 'judge') return '概念判断错误'
  if (qtype === 'short') return '表述应用不足'
  return '概念理解混淆'
}

function parseTime(iso) {
  if (!iso) return null
  const t = new Date(iso).getTime()
  return Number.isNaN(t) ? null : t
}

/** 按评估周期过滤错题（上期报告时间 ~ 本期报告时间） */
export function filterWrongByPeriod(items, periodStart, periodEnd) {
  const start = parseTime(periodStart)
  const end = parseTime(periodEnd)
  return (items || []).filter((item) => {
    const t = parseTime(item.created_at)
    if (!t) return true
    if (start && t < start) return false
    if (end && t > end) return false
    return true
  })
}

/** 实时 API 错题聚合 */
export function aggregateWrongAnalysis(items) {
  const list = items || []
  const kpMap = {}
  const typeMap = {}
  let reviewed = 0

  for (const item of list) {
    const kp = item.kp_name || item.module_name || '未标注知识点'
    kpMap[kp] = (kpMap[kp] || 0) + 1
    const et = categorizeErrorType(item)
    typeMap[et] = (typeMap[et] || 0) + 1
    if (item.reviewed) reviewed += 1
  }

  const topKp = Object.entries(kpMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)

  const errorTypes = Object.entries(typeMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const total = list.length
  const correctionRate = total ? Math.round((reviewed / total) * 100) : 0

  return { topKp, errorTypes, total, reviewed, correctionRate }
}

/** 历史报告列表补充较上次变化 */
export function enrichHistoryDeltas(items) {
  const sorted = [...(items || [])].sort((a, b) => b.id - a.id)
  return sorted.map((item, i) => {
    const prev = sorted[i + 1]
    const delta =
      prev != null
        ? Math.round((Number(item.overall_score) - Number(prev.overall_score)) * 10) / 10
        : null
    return { ...item, score_delta: delta }
  })
}

/** 从历次评估详情构建趋势序列 */
export function buildEvalTrendSeries(evalDetails, filterKey) {
  const sorted = [...(evalDetails || [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )

  const labels = sorted.map((e) => `RPT-${e.id}`)
  const values = sorted.map((e) => {
    const metrics = e.metrics || {}
    if (filterKey === 'total') return Number(e.overall_score) || 0

    if (filterKey.startsWith('stage_')) {
      const stageNum = Number(filterKey.replace('stage_', ''))
      const st = (metrics.stage_balance || []).find((s) => s.stage === stageNum)
      return st ? Number(st.avg_score) || 0 : 0
    }

    if (filterKey.startsWith('module_')) {
      const modIdx = Number(filterKey.replace('module_', ''))
      const modName = MODULE_NAMES[modIdx]
      const scores = metrics.module_scores || []
      const found = scores.find((m) => m.module_name === modName)
      if (found) return Number(found.avg_score) || 0
      const modules = metrics.modules || []
      const legacy = modules.find((m) => m.module_name === modName)
      return legacy ? Number(legacy.avg_score || legacy.final_score) || 0 : 0
    }

    return Number(e.overall_score) || 0
  })

  return { labels, values, count: sorted.length }
}

export function getTrendFilterOptions() {
  const opts = [{ value: 'total', label: '总分走势' }]
  for (const st of LEARNING_STAGES) {
    opts.push({ value: `stage_${st.stage}`, label: st.stage_name })
  }
  MODULE_NAMES.forEach((name, i) => {
    opts.push({ value: `module_${i}`, label: name })
  })
  return opts
}

/** 匹配建议文本中的模块名 */
export function matchModuleFromText(text, moduleScores = []) {
  const scores = moduleScores.length
    ? moduleScores
    : MODULE_NAMES.map((name, i) => ({ module_id: i + 1, module_name: name }))
  for (const m of scores) {
    if (text.includes(m.module_name)) return m
  }
  return null
}

export function formatDelta(v) {
  if (v == null || v === 0) return '0'
  return v > 0 ? `+${v}` : String(v)
}
