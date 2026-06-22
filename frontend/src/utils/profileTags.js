/** 将后端 JSON 字符串解析为字符串数组（展示用） */
export function parseStringArray(jsonStr) {
  if (!jsonStr || typeof jsonStr !== 'string') return []
  const t = jsonStr.trim()
  if (!t || t === '[]') return []
  try {
    const v = JSON.parse(t)
    if (!Array.isArray(v)) return []
    return v.map((x) => (typeof x === 'string' ? x : String(x))).filter(Boolean)
  } catch {
    return [t]
  }
}

/** 掌握度标签：[{ subject, level }] */
export function parseMasteryTags(jsonStr) {
  if (!jsonStr || typeof jsonStr !== 'string') return []
  const t = jsonStr.trim()
  if (!t || t === '[]') return []
  try {
    const v = JSON.parse(t)
    if (!Array.isArray(v)) return []
    return v
      .map((item) => {
        if (item && typeof item === 'object') {
          return {
            subject: item.subject || '',
            level: item.level || '',
          }
        }
        return null
      })
      .filter((x) => x && (x.subject || x.level))
  } catch {
    return []
  }
}

export function stringifyStringArray(arr) {
  const list = (arr || []).map((s) => String(s).trim()).filter(Boolean)
  return JSON.stringify(list)
}

export function stringifyMasteryTags(list) {
  const items = (list || [])
    .filter((x) => x && (x.subject || x.level))
    .map((x) => ({
      subject: x.subject || '',
      level: x.level || '',
    }))
  return JSON.stringify(items)
}
