/**
 * 从本地运行的 Flask / Java 后端导出指定学生的静态演示数据。
 *
 * 用法（PowerShell）：
 *   cd static-demo
 *   $env:STUDENT_ID="7"          # 用户07 的数据库 ID，按实际修改
 *   node export.mjs
 *
 * 按用户名查找（需管理员账号）：
 *   $env:STUDENT_USERNAME="07"
 *   $env:ADMIN_USERNAME="admin"
 *   $env:ADMIN_PASSWORD="你的密码"
 *   node export.mjs
 */
import { writeFileSync, copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUT_DIR = join(__dirname, 'site')
const DATA_FILE = join(OUT_DIR, 'data.json')

const FLASK = process.env.FLASK_URL || 'http://127.0.0.1:5001'
const JAVA = process.env.JAVA_URL || 'http://127.0.0.1:8080'
const COURSE_ID = process.env.COURSE_ID || 'python101'

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${url} → HTTP ${res.status}${text ? `: ${text.slice(0, 200)}` : ''}`)
  }
  return res.json()
}

async function loginAdmin() {
  const username = process.env.ADMIN_USERNAME
  const password = process.env.ADMIN_PASSWORD
  if (!username || !password) return null
  const body = await fetchJson(`${JAVA}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  return body.data?.token || body.token || null
}

async function resolveStudentId(token) {
  if (process.env.STUDENT_ID) return Number(process.env.STUDENT_ID)

  const keyword = process.env.STUDENT_USERNAME
  if (keyword && token) {
    const res = await fetchJson(`${JAVA}/api/auth/students?keyword=${encodeURIComponent(keyword)}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const list = res.data || []
    const exact = list.find((s) => s.username === keyword)
    const partial = list.find((s) => String(s.username).includes(keyword))
    const hit = exact || partial
    if (!hit) throw new Error(`找不到用户名含「${keyword}」的学生，请设置 STUDENT_ID`)
    console.log(`按用户名「${keyword}」匹配到：ID=${hit.id} username=${hit.username}`)
    return hit.id
  }

  console.warn('未设置 STUDENT_ID，默认使用 7（用户07）。可用 $env:STUDENT_ID="7" 指定。')
  return 7
}

function fmtSessionLabel(iso) {
  if (!iso) return '未知时间'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16)
  return d.toLocaleString('zh-CN', { hour12: false })
}

function buildDialogueSessions(studentId, tutoringRes) {
  const tutoringMsgs = (tutoringRes?.messages || []).filter(
    (m) =>
      m.role === 'user' ||
      m.role === 'assistant' ||
      m.msg_type === 'mastery_update'
  )
  if (!tutoringMsgs.length) return []

  return [
    {
      session_id: tutoringRes.session_id || `tutor-${studentId}`,
      label: `智能辅导 · ${fmtSessionLabel(tutoringMsgs[0]?.created_at)}`,
      started_at: tutoringMsgs[0]?.created_at,
      ended_at: tutoringMsgs[tutoringMsgs.length - 1]?.created_at,
      message_count: tutoringMsgs.length,
      messages: tutoringMsgs
    }
  ]
}

async function exportStudent(studentId, token) {
  console.log(`正在导出学生 ID=${studentId} …`)
  console.log(`Flask: ${FLASK}`)

  const [mastery, wrong, history, tutoringRes, basicRes] = await Promise.all([
    fetchJson(`${FLASK}/api/profile-build/mastery/${studentId}`),
    fetchJson(`${FLASK}/api/profile-build/wrong-questions/${studentId}?limit=200`),
    fetchJson(`${FLASK}/api/profile-build/history/all/${studentId}`),
    fetchJson(`${FLASK}/api/profile-build/tutoring/history/${studentId}`),
    fetchJson(`${FLASK}/api/profile-build/v1/courses/${COURSE_ID}/profile/basic/${studentId}`)
  ])

  let profile = null
  if (token) {
    try {
      const res = await fetchJson(`${JAVA}/api/profile/${studentId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      profile = res.data || null
      console.log('已附加 Java 画像详情（含薄弱点等）')
    } catch (e) {
      console.warn('Java 画像接口跳过：', e.message)
    }
  }

  const basic = basicRes.data || {}
  const weakPoints = profile?.weakPoints
    ? tryParseJsonArray(profile.weakPoints)
    : []

  return {
    exported_at: new Date().toISOString(),
    student_id: studentId,
    title: `${basic.real_name || '学习者'} · 学习演示`,
    basic: {
      real_name: basic.real_name || profile?.realName || '',
      grade: basic.grade || profile?.grade || '',
      major: basic.major || profile?.major || '',
      learn_preferences: basic.learn_preferences || profile?.learnPreferences || ''
    },
    mastery,
    wrong,
    history,
    dialogue_sessions: buildDialogueSessions(studentId, tutoringRes),
    profile,
    weak_points: weakPoints
  }
}

function tryParseJsonArray(raw) {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : [String(raw)]
  } catch {
    return String(raw)
      .split(/[,，;；]/)
      .map((s) => s.trim())
      .filter(Boolean)
  }
}

function ensureSiteFiles() {
  mkdirSync(OUT_DIR, { recursive: true })
  const htmlSrc = join(__dirname, 'template', 'index.html')
  const htmlDst = join(OUT_DIR, 'index.html')
  if (existsSync(htmlSrc)) {
    copyFileSync(htmlSrc, htmlDst)
  }
}

async function main() {
  let token = null
  try {
    token = await loginAdmin()
  } catch (e) {
    console.warn('管理员登录失败，将只导出 Flask 数据：', e.message)
  }

  const studentId = await resolveStudentId(token)
  const payload = await exportStudent(studentId, token)

  ensureSiteFiles()
  writeFileSync(DATA_FILE, JSON.stringify(payload, null, 2), 'utf8')

  console.log('')
  console.log('导出完成！')
  console.log(`  文件：${DATA_FILE}`)
  console.log(`  学生：${payload.basic.real_name || '(未填姓名)'} (ID=${studentId})`)
  console.log(`  画像模块：${payload.mastery?.modules?.length || 0} 个`)
  console.log(`  错题：${payload.wrong?.items?.length || 0} 道`)
  console.log(`  对话会话：${payload.dialogue_sessions?.length || 0} 个`)
  console.log(`  对话消息：${(payload.dialogue_sessions || []).reduce((n, s) => n + (s.message_count || 0), 0)} 条`)
  console.log('')
  console.log('下一步：')
  console.log('  1. 用浏览器打开 static-demo/site/index.html 预览')
  console.log('  2. 将 static-demo/site/ 目录内全部文件上传到 Gitee Pages 仓库')
  console.log('  3. 报告里写 Gitee Pages 给的链接')
}

main().catch((err) => {
  console.error('导出失败：', err.message)
  console.error('')
  console.error('请确认：')
  console.error('  · MySQL 已启动')
  console.error('  · Flask 已运行（cd profile_flask && python app.py）')
  console.error('  · STUDENT_ID 是否正确（用户07 可能是 id=7，先用数据库确认）')
  process.exit(1)
})
