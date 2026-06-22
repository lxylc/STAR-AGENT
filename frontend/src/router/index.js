import { createRouter, createWebHistory } from 'vue-router'
import { clearAuth, getToken, getStoredUser } from '../api/auth'
import ProfileDialogue from '../views/ProfileDialogue.vue'
import ProfileView from '../views/ProfileView.vue'
import ResourceCenter from '../views/ResourceCenter.vue'
import PersonalizedResourceView from '../views/PersonalizedResourceView.vue'
import LearningPathCenter from '../views/LearningPathCenter.vue'
import LearnZoneView from '../views/LearnZoneView.vue'
import HomeView from '../views/HomeView.vue'
import EvaluationView from '../views/EvaluationView.vue'
import HistoryView from '../views/HistoryView.vue'
import WrongQuestionReviewView from '../views/WrongQuestionReviewView.vue'
import ExerciseCenterView from '../views/ExerciseCenterView.vue'
import AuthView from '../views/AuthView.vue'
import Settings from '../views/Settings.vue'
import StudentList from '../views/admin/StudentList.vue'

// 每次打开应用清除本地登录态，始终从登录页进入
clearAuth()

const routes = [
  { path: '/login', component: AuthView, meta: { public: true } },
  { path: '/register', component: AuthView, meta: { public: true } },
  { path: '/demo', component: ProfileView, meta: { public: true, demo: true } },
  { path: '/', redirect: '/login' },
  { path: '/chat', component: HomeView },
  { path: '/history', component: HistoryView },
  { path: '/settings', component: Settings },
  { path: '/profile/dialogue', component: ProfileDialogue },
  { path: '/profile/self-build', redirect: '/profile/dialogue' },
  { path: '/profile/view', component: ProfileView },
  { path: '/resource', component: ResourceCenter },
  { path: '/resource/personalized', component: PersonalizedResourceView },
  { path: '/path', component: LearningPathCenter },
  { path: '/tutoring', redirect: (to) => ({ path: '/chat', query: to.query }) },
  { path: '/evaluation', component: EvaluationView },
  { path: '/learn/zone', component: LearnZoneView },
  { path: '/learn/wrong-review', component: WrongQuestionReviewView },
  { path: '/learn/exercise-center', component: ExerciseCenterView },
  { path: '/learn/practice', redirect: (to) => ({ path: '/learn/exercise-center', query: { ...to.query, mode: to.query.mode || 'special' } }) },
  { path: '/learn/module-practice', redirect: (to) => ({ path: '/learn/exercise-center', query: { ...to.query, mode: to.query.mode || 'module' } }) },
  { path: '/admin/students', component: StudentList, meta: { admin: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  if (to.path === '/chat' && to.query.view === 'history') {
    return { path: '/history' }
  }
  if (to.meta.public) return true
  if (!getToken()) return '/login'
  const user = getStoredUser()
  if (to.meta.admin) {
    if (user?.role !== 'admin') return '/chat'
    return true
  }
  if (user?.role === 'admin') {
    if (to.meta.admin) return true
    if ((to.path === '/profile/view' || to.path === '/evaluation') && to.query.studentId) {
      return true
    }
    return '/admin/students'
  }
  return true
})

export default router
