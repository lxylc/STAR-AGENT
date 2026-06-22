import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
  breaks: true,
  gfm: true
})

function looksLikeMarkdownProse(text) {
  return (
    /(^|\n)#{1,6}\s+\S/m.test(text) ||
    /\*\*[^*]+\*\*/.test(text) ||
    /(^|\n)[-*]\s+\S/m.test(text) ||
    /(^|\n)\d+\.\s+\S/m.test(text)
  )
}

function looksLikeCode(text) {
  return /^\s*(def |class |import |from |print\(|if __name__|function |const |let |var |public |private )/m.test(
    text
  )
}

/** 是否包含完整的 fenced 代码块（不应被 unwrap 逻辑破坏） */
function hasValidFencedCodeBlock(text) {
  return /```[\w-]*\s*\n[\s\S]*?\n```/.test(text || '')
}

/** 星火常把 Markdown 讲义误包进 ``` 围栏，展开为正文以便排版渲染。 */
function unwrapProseFences(text) {
  let out = text

  // 含正常代码块时，仅展开 markdown/md 误包裹，避免破坏案例展示结构
  if (hasValidFencedCodeBlock(out)) {
    return out.replace(/```(?:markdown|md)\s*\n([\s\S]*?)```/gi, (_, inner) => inner.trim())
  }

  // 全文单层围栏
  if (/^```[\w]*\s*\n[\s\S]*```\s*$/i.test(out)) {
    const lang = (out.match(/^```(\w+)/) || [])[1] || ''
    const inner = out.replace(/^```\w*\s*\n/i, '').replace(/\n```\s*$/, '').trim()
    if (
      /^(?:markdown|md)$/i.test(lang) ||
      (!lang && looksLikeMarkdownProse(inner) && !looksLikeCode(inner) && !/```/.test(inner))
    ) {
      out = inner
    }
  }

  // 文中误包的 markdown/md 围栏
  out = out.replace(/```(?:markdown|md)\s*\n([\s\S]*?)```/gi, (_, inner) => inner.trim())

  // 讲义正文围栏，后接真实代码块（```python 等）
  out = out.replace(
    /(^|[\r\n]+)```[ \t]*[\r\n]+((?:[^`]|`(?!``))*?)[\r\n]+```[ \t]*(?=[\r\n]+```(?:python|py|javascript|js|java|json)\b)/gim,
    '$1$2'
  )

  // 讲义正文围栏，后接下一章节标题
  out = out.replace(
    /(^|[\r\n]+)```[ \t]*[\r\n]+((?:[^`]|`(?!``))*?)[\r\n]+```[ \t]*(?=[\r\n]+## )/gim,
    '$1$2'
  )

  // 章节内未配对的起始围栏（如「## 知识点讲义」后的 ```）
  out = out.replace(/(^|[\r\n]{2,})```[ \t]*[\r\n]+(?=#{1,6}\s)/gm, '$1')

  // 未闭合围栏：全文以 ``` 开头且后接标题
  if (/^```\w*\s*\n/.test(out) && /(^|\n)#{1,6}\s+\S/m.test(out)) {
    out = out.replace(/^```\w*\s*\n/, '')
  }

  return out
}

/**
 * 清洗 AI 生成的 Markdown，去除无意义符号与空标题。
 */
export function cleanMarkdownContent(raw) {
  if (!raw) return ''
  let text = String(raw).trim()

  text = unwrapProseFences(text)

  // 全文被代码块包裹（json 误包裹时保留，供辅导 JSON 解析）
  if (/^```(?:json)?\s*\n[\s\S]*```\s*$/i.test(text)) {
    const inner = text.replace(/^```(?:json)?\s*\n/i, '').replace(/\n```\s*$/, '').trim()
    if (!inner.startsWith('{') || !/"text_answer"\s*:/.test(inner)) {
      text = unwrapProseFences(inner)
    }
  }

  // 空标题行
  text = text.replace(/^#{1,6}\s*$/gm, '')

  // 「# # 标题」重复井号
  text = text.replace(/^(#{1,6})\s+(#\s+)+/gm, '$1 ')

  // 讲义正文内一级标题降为二级（与智能体 Prompt 一致）
  text = text.replace(/^# (?!#)/gm, '## ')

  // 压缩过多空行
  text = text.replace(/\n{4,}/g, '\n\n\n')

  return text.trim()
}

export function renderMarkdown(raw) {
  const cleaned = cleanMarkdownContent(raw)
  if (!cleaned) return ''
  const html = marked.parse(cleaned)
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ['target', 'rel']
  })
}

export function extractCodeBlock(text) {
  const m = (text || '').match(/```[\w-]*\n?([\s\S]*?)```/)
  return m ? m[1].trim() : (text || '').trim()
}

/**
 * 将 Markdown 拆成「代码块前正文 / 代码 / 代码块后正文」。
 * 代码案例页用分段渲染，避免 marked 把后续标题误吞进代码块。
 */
export function splitMarkdownCodeSections(raw) {
  const text = String(raw || '').trim()
  const match = text.match(/^([\s\S]*?)```([\w-]+)?\s*\n([\s\S]*?)\n```\s*([\s\S]*)$/)
  if (!match) {
    return { before: text, language: 'python', code: '', after: '' }
  }
  return {
    before: match[1].trim(),
    language: match[2] || 'python',
    code: match[3].trim(),
    after: match[4].trim()
  }
}

/** 去掉 Markdown 中的代码块，保留题目说明等正文。 */
export function extractProseWithoutCode(text) {
  return cleanMarkdownContent(text || '')
    .replace(/```[\w]*\n?[\s\S]*?```/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * 尝试解析习题 JSON，供结构化展示。
 */
export function parseExerciseJson(jsonStr) {
  if (!jsonStr) return null
  try {
    let t = jsonStr.trim()
    if (t.startsWith('```')) {
      t = t.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/```\s*$/, '')
    }
    const start = t.indexOf('{')
    const end = t.lastIndexOf('}')
    if (start >= 0 && end > start) {
      t = t.slice(start, end + 1)
    }
    return JSON.parse(t)
  } catch {
    return null
  }
}

export function formatExerciseForDisplay(exercise) {
  if (!exercise) return null
  const sections = []
  const single = exercise.singleChoice || exercise.single_choice || []
  const multi = exercise.multiChoice || exercise.multi_choice || []
  const short = exercise.shortAnswer || exercise.short_answer || []

  if (single.length) {
    sections.push({
      title: '单选题',
      items: single.map((q, i) => ({
        no: i + 1,
        question: q.question,
        options: q.options || [],
        answer: q.answer,
        analysis: q.analysis
      }))
    })
  }
  if (multi.length) {
    sections.push({
      title: '多选题',
      items: multi.map((q, i) => ({
        no: i + 1,
        question: q.question,
        options: q.options || [],
        answer: Array.isArray(q.answer) ? q.answer.join('、') : q.answer,
        analysis: q.analysis
      }))
    })
  }
  if (short.length) {
    sections.push({
      title: '简答题',
      items: short.map((q, i) => ({
        no: i + 1,
        question: q.question,
        answer: q.answer,
        analysis: q.analysis
      }))
    })
  }
  return sections.length ? sections : null
}
