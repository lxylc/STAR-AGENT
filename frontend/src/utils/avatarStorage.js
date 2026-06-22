import { ref, computed } from 'vue'

const avatarVersion = ref(0)

export function getAvatarUrl(studentId) {
  if (!studentId) return ''
  return localStorage.getItem(`avatar_${studentId}`) || ''
}

export function setAvatarUrl(studentId, dataUrl) {
  if (!studentId) return
  if (dataUrl) localStorage.setItem(`avatar_${studentId}`, dataUrl)
  else localStorage.removeItem(`avatar_${studentId}`)
  avatarVersion.value++
}

export function useAvatarUrl(studentIdRef) {
  return computed(() => {
    avatarVersion.value
    const id = typeof studentIdRef === 'function' ? studentIdRef() : studentIdRef?.value
    return getAvatarUrl(id)
  })
}

export function getDisplayInitial(user) {
  const name = user?.realName || user?.username || 'U'
  return name.charAt(0).toUpperCase()
}

export function readImageAsAvatar(file, maxSize = 128) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const img = new Image()
      img.onload = () => {
        const scale = Math.min(maxSize / img.width, maxSize / img.height, 1)
        const w = Math.round(img.width * scale)
        const h = Math.round(img.height * scale)
        const canvas = document.createElement('canvas')
        canvas.width = w
        canvas.height = h
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, w, h)
        resolve(canvas.toDataURL('image/jpeg', 0.85))
      }
      img.onerror = () => reject(new Error('图片加载失败'))
      img.src = reader.result
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}
