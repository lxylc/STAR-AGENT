/** 基础信息与学习偏好选项（个人设置 / 画像页共用） */
export const GRADE_OPTIONS = ['大一', '大二', '大三', '大四', '研究生', '其他']
export const MAJOR_OPTIONS = [
  '计算机科学与技术',
  '软件工程',
  '人工智能',
  '数据科学',
  '电子信息',
  '其他'
]
export const LEARN_PREF_OPTIONS = ['理论阅读', '代码实操', '例题演练', '视频讲解', '图文图解']

export function parseLearnPreferences(raw) {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  try {
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch {
    return raw ? [String(raw)] : []
  }
}

export function formatLearnPreferences(raw) {
  const arr = parseLearnPreferences(raw)
  return arr.length ? arr.join('、') : '-'
}
