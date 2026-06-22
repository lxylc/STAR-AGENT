/**
 * 解析智能辅导 JSON（兼容 ```json 包裹、前后杂文本）。
 */
export function parseTutoringJson(raw) {
  if (!raw) return null
  if (typeof raw === 'object' && !Array.isArray(raw)) return raw

  let text = String(raw).trim()
  if (!text) return null

  if (text.startsWith('```')) {
    text = text.replace(/^```(?:json|JSON)?\s*\n?/i, '').replace(/\n?```\s*$/i, '').trim()
  }

  const start = text.indexOf('{')
  const end = text.lastIndexOf('}')
  if (start >= 0 && end > start) {
    text = text.slice(start, end + 1)
  }

  try {
    const data = JSON.parse(text)
    return typeof data === 'object' && data && !Array.isArray(data) ? data : null
  } catch {
    return null
  }
}

function mergeTutoringFields(base, parsed) {
  if (!parsed || typeof parsed !== 'object') return base

  const merged = { ...base }
  if (typeof parsed.text_answer === 'string' && parsed.text_answer.trim()) {
    merged.text_answer = parsed.text_answer.trim()
  }
  if (parsed.diagram && typeof parsed.diagram === 'object') {
    merged.diagram = { ...(merged.diagram || {}), ...parsed.diagram }
  }
  if (Array.isArray(parsed.bilibili_videos) && parsed.bilibili_videos.length) {
    merged.bilibili_videos = parsed.bilibili_videos
  }
  if (Array.isArray(parsed.code_snippets) && parsed.code_snippets.length) {
    merged.code_snippets = parsed.code_snippets
  }
  if (parsed.video_script && typeof parsed.video_script === 'object') {
    merged.video_script = { ...(merged.video_script || {}), ...parsed.video_script }
  }
  if (Array.isArray(parsed.follow_up_actions) && parsed.follow_up_actions.length) {
    merged.follow_up_actions = parsed.follow_up_actions
  }
  if (Array.isArray(parsed.related_kps) && parsed.related_kps.length) {
    merged.related_kps = parsed.related_kps
  }
  return merged
}

function appendCodeSnippets(text, snippets) {
  const body = (text || '').trim()
  const items = (snippets || []).map((s) => String(s).trim()).filter(Boolean)
  if (!items.length) return body
  const blocks = items.map((snip, idx) => `**代码示例 ${idx + 1}：**\n\n\`\`\`python\n${snip.replace(/\\n/g, '\n')}\n\`\`\``)
  return [body, ...blocks].filter(Boolean).join('\n\n')
}

/**
 * 修正 payload：当 text_answer 误存整段 JSON 时，拆出真正字段供组件渲染。
 */
export function normalizeTutoringPayload(payload) {
  if (!payload) return null
  if (typeof payload === 'string') {
    const parsed = parseTutoringJson(payload)
    return parsed ? normalizeTutoringPayload(parsed) : { text_answer: payload }
  }
  if (typeof payload !== 'object') return payload

  let normalized = { ...payload }

  if (typeof normalized.text_answer === 'string') {
    const trimmed = normalized.text_answer.trim()
    if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
      const parsed = parseTutoringJson(trimmed)
      if (parsed?.text_answer) {
        normalized = mergeTutoringFields(normalized, parsed)
      }
    }
  }

  if (typeof normalized.content === 'string' && !normalized.text_answer) {
    const parsed = parseTutoringJson(normalized.content)
    if (parsed?.text_answer) {
      normalized = mergeTutoringFields(normalized, parsed)
    } else if (normalized.content.trim() && !normalized.content.trim().startsWith('{')) {
      normalized.text_answer = normalized.content.trim()
    }
  }

  if (Array.isArray(normalized.code_snippets) && normalized.code_snippets.length) {
    normalized.text_answer = appendCodeSnippets(normalized.text_answer, normalized.code_snippets)
  }

  return normalized
}
