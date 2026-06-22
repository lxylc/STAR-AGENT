/** 资源推荐优先级排序权重 */
export const PRIORITY_ORDER = {
  eval: 0,
  profile: 1,
  ai: 2,
  extend: 3
}

export const PRIORITY_LABELS = {
  eval: '评估补强',
  profile: '学情推荐',
  ai: 'AI协同生成',
  extend: '拓展自选'
}

export function sortPersonalizedResources(list) {
  return [...(list || [])].sort((a, b) => {
    const oa = a.priority_order ?? PRIORITY_ORDER.profile
    const ob = b.priority_order ?? PRIORITY_ORDER.profile
    if (oa !== ob) return oa - ob
    const sa = Number(a.module_score ?? 999)
    const sb = Number(b.module_score ?? 999)
    if (sa !== sb) return sa - sb
    if (a.createdAt && b.createdAt) {
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    }
    return 0
  })
}

export function enrichAiResource(r, plan) {
  const focus = new Set(plan?.basis?.evaluation_focus_modules || [])
  const mp = (plan?.module_plans || []).find(
    (m) => r.knowledgePoint?.includes(m.module_name) || m.knowledge_point === r.knowledgePoint
  )
  const moduleName = mp?.module_name || ''
  const isEval = moduleName && focus.has(moduleName)
  const tier = isEval ? 'eval' : 'ai'
  return {
    ...r,
    resourceType: r.resourceType || r.resource_type,
    contentJson: r.contentJson || r.content_json,
    preview: false,
    priority_tier: tier,
    priority_order: PRIORITY_ORDER[tier],
    priority_label: PRIORITY_LABELS[tier],
    recommend_reason: isEval
      ? `评估补强：星火多智能体为「${moduleName}」生成定制资源`
      : (r.resourceType || r.resource_type) === 'courseware'
        ? `学情推荐：「${moduleName}」优秀代码案例，供观看学习`
        : `AI协同生成：多智能体流水线产出（讲义 / 习题 / 课件）`,
    module_id: mp?.module_id,
    module_name: moduleName,
    module_score: mp?.final_score
  }
}

export function buildRecommendSummary(plan) {
  if (!plan?.basis) return ''
  const modulePlans = plan.module_plans || []
  const evalCount =
    plan.basis.batch_eval_count ??
    modulePlans.filter((mp) => mp.is_evaluation_focus).length
  const profileCount =
    plan.basis.batch_profile_count ?? Math.max(0, modulePlans.length - evalCount)
  const count = modulePlans.length
  const evalTotal = (plan.basis.evaluation_focus_modules || []).length

  if (evalCount || profileCount) {
    let text = `本批优先推送 ${evalCount} 个评估补强模块、${profileCount} 个学情推荐模块的配套资源（共 ${count} 个模块）。`
    if (evalTotal > evalCount) {
      text += ` 评估共标记 ${evalTotal} 个薄弱模块，本批按得分优先覆盖其中 ${evalCount} 个。`
    }
    return text
  }

  const profileWeak = plan.basis.profile_weak_modules || []
  if (profileWeak.length) {
    return `根据画像薄弱模块「${profileWeak.slice(0, 2).join('、')}」等，匹配 ${count} 个模块的即时推荐资源。`
  }
  return plan.summary_line || '根据当前学情生成个性化资源推荐。'
}

export function countByTier(resources) {
  const stats = { total: resources.length, eval: 0, profile: 0, ai: 0, extend: 0 }
  for (const r of resources) {
    const t = r.priority_tier || (r.preview ? 'profile' : 'ai')
    if (stats[t] != null) stats[t] += 1
  }
  return stats
}
