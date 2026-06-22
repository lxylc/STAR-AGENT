/** 综合评级（基于整体平均分） */
export function computeOverallRating(avgScore) {
  if (avgScore == null || Number.isNaN(avgScore)) return { label: '-', level: 'none' }
  const s = Number(avgScore)
  if (s >= 85) return { label: '优秀', level: 'excellent' }
  if (s >= 70) return { label: '良好', level: 'good' }
  if (s >= 45) return { label: '一般', level: 'fair' }
  return { label: '待加强', level: 'weak' }
}

/** TOP3 薄弱模块（分数最低的三个） */
export function getTopWeakModules(modules, limit = 3) {
  return [...(modules || [])]
    .filter((m) => m.final_score != null)
    .sort((a, b) => Number(a.final_score) - Number(b.final_score))
    .slice(0, limit)
}

/** TOP3 优势模块（分数最高的三个） */
export function getTopStrongModules(modules, limit = 3) {
  return [...(modules || [])]
    .filter((m) => m.final_score != null)
    .sort((a, b) => Number(b.final_score) - Number(a.final_score))
    .slice(0, limit)
}

/** 从快照序列计算历次测评平均分（时间正序） */
export function buildTrendPoints(snapshots) {
  const sorted = [...(snapshots || [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
  return sorted
    .map((snap) => {
      const scores = snap.scores && typeof snap.scores === 'object' ? Object.values(snap.scores) : []
      const nums = scores.map((s) => Number(s.final_score)).filter((n) => !Number.isNaN(n))
      if (!nums.length) return null
      const avg = Math.round(nums.reduce((a, b) => a + b, 0) / nums.length)
      return {
        date: formatDateLabel(snap.created_at),
        fullDate: snap.created_at,
        score: avg
      }
    })
    .filter(Boolean)
}

function formatDateLabel(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function formatDateTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day} ${h}:${min}`
}

/** 学情标签项（含跳转所需元数据） */
function makeTagItem(mod, tagType, tagContent) {
  return {
    tagType,
    tagContent,
    moduleId: mod.module_id,
    moduleName: mod.module_name,
    label: `${mod.module_name}：${tagContent}`,
    navigable: mod.module_id != null
  }
}

function pushTag(list, seen, item) {
  const key = `${item.tagType}-${item.moduleId}-${item.tagContent}`
  if (seen.has(key)) return
  seen.add(key)
  list.push(item)
}

function hasModuleWeaknessTag(seen, moduleId) {
  return [...seen].some((key) => key.startsWith(`weakness-${moduleId}-`))
}

function moduleLooksWeak(mod) {
  const kps = mod.knowledge_points || []
  if (kps.some((kp) => kp.master_level <= 2)) return true
  const score = mod.final_score
  return score != null && !Number.isNaN(Number(score)) && Number(score) < 70
}

/** 聚合三类学情标签（知识短板 / 代码实操 / 练习频次） */
export function aggregateTagGroups(modules) {
  const weaknessItems = []
  const codeItems = []
  const practiceItems = []
  const seen = new Set()

  for (const mod of modules || []) {
    const tags = mod.tags || {}
    if (tags.weakness_type && tags.weakness_type !== '无短板') {
      pushTag(weaknessItems, seen, makeTagItem(mod, 'weakness', tags.weakness_type))
    }
    if (tags.code_practice_feel) {
      pushTag(codeItems, seen, makeTagItem(mod, 'code', tags.code_practice_feel))
    }
    if (tags.practice_frequency) {
      pushTag(practiceItems, seen, makeTagItem(mod, 'practice', tags.practice_frequency))
    }
  }

  for (const mod of modules || []) {
    if (mod.module_id == null || hasModuleWeaknessTag(seen, mod.module_id)) continue
    if (!moduleLooksWeak(mod)) continue
    pushTag(weaknessItems, seen, makeTagItem(mod, 'weakness', '待加强'))
  }

  return [
    { key: 'weakness', title: '知识短板标签', items: weaknessItems },
    { key: 'code', title: '代码实操标签', items: codeItems },
    { key: 'practice', title: '练习频次标签', items: practiceItems }
  ]
}

/** 个性化练习建议 */
export function buildPracticeSuggestions(modules, summary) {
  const suggestions = []
  const weak = getTopWeakModules(modules, 3)

  weak.forEach((m) => {
    const freq = m.tags?.practice_frequency || ''
    if (freq === '很少练习') {
      suggestions.push(`「${m.module_name}」得分 ${m.final_score} 且练习偏少，建议每周完成 2~3 道相关编程题。`)
    } else {
      suggestions.push(`重点巩固「${m.module_name}」（当前 ${m.final_score} 分），结合章节案例动手实践。`)
    }
  })

  const lowPractice = (modules || []).filter((m) => m.tags?.practice_frequency === '很少练习')
  if (lowPractice.length >= 3 && !suggestions.some((s) => s.includes('练习偏少'))) {
    suggestions.push('多个模块练习频次偏低，建议制定固定实操计划，以项目小练习带动知识巩固。')
  }

  const avg = summary?.avg_score
  if (avg != null && avg >= 70 && weak.every((m) => Number(m.final_score) >= 45)) {
    suggestions.push('整体掌握较好，可通过综合项目或阶段性测验保持熟练度。')
  }

  if (!suggestions.length) {
    suggestions.push('保持当前学习节奏，定期回顾已学模块并进行综合练习。')
  }
  return suggestions
}

/** 学习成长时间轴事件（最新置顶） */
export function buildTimelineEvents(snapshots, changeLogs) {
  const events = []
  const sortedSnaps = [...(snapshots || [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )

  sortedSnaps.forEach((snap, idx) => {
    events.push({
      datetime: snap.created_at,
      title: idx === 0 ? '首次生成画像' : '重新构建画像',
      description:
        snap.interpretation ||
        (idx === 0 ? '完成首次测评，系统生成专属学习画像。' : `完成第 ${idx + 1} 次完整测评，画像已更新。`)
    })
  })

  for (const log of changeLogs || []) {
    if (log.field_name === 'profile_snapshot') continue

    if (log.source === 'module_practice') {
      const name = (log.field_name || '').replace(/^module_score:/, '') || '模块'
      events.push({
        datetime: log.created_at,
        title: `完成「${name}」模块练习`,
        description: `练习后分数 ${log.old_value ?? '-'} → ${log.new_value ?? '-'}`
      })
      continue
    }

    if (log.source === 'admin') {
      events.push({
        datetime: log.created_at,
        title: '管理员修改分数',
        description: `字段「${log.field_name}」：${log.old_value ?? '-'} → ${log.new_value ?? '-'}`
      })
      continue
    }

    if (log.source === 'qa' || /^kp:/.test(log.field_name || '')) {
      const name = (log.field_name || '').replace(/^kp:/, '')
      events.push({
        datetime: log.created_at,
        title: '薄弱模块变更',
        description: `「${name || log.field_name}」掌握度 ${log.old_value ?? '-'} → ${log.new_value ?? '-'}`
      })
      continue
    }

    if (/weak|module_score|mastery/i.test(log.field_name || '')) {
      events.push({
        datetime: log.created_at,
        title: '薄弱模块变更',
        description: `${log.field_name}：${log.old_value ?? '-'} → ${log.new_value ?? '-'}`
      })
    }
  }

  return events
    .map((e) => ({ ...e, datetimeLabel: formatDateTime(e.datetime) }))
    .sort((a, b) => new Date(b.datetime).getTime() - new Date(a.datetime).getTime())
}
