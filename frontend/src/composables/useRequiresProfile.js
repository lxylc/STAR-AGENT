import { ref, onMounted } from 'vue'
import { getProfile } from '../api/profile'
import { getStudentId } from '../api/auth'

export function useRequiresProfile() {
  const loading = ref(true)
  const profileCompleted = ref(false)

  async function checkProfile() {
    loading.value = true
    try {
      const sid = getStudentId()
      if (!sid) {
        profileCompleted.value = false
        return
      }
      const profile = await getProfile(sid)
      profileCompleted.value = profile?.profileStatus === 'completed'
    } catch {
      profileCompleted.value = false
    } finally {
      loading.value = false
    }
  }

  onMounted(checkProfile)

  return { loading, profileCompleted, checkProfile }
}
