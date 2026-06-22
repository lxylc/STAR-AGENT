<template>
  <div v-if="isAuthPage || isStandalone" class="auth-shell" :class="{ 'standalone-shell': isStandalone }">
    <router-view />
  </div>

  <div v-else class="app-shell">
    <AppSidebar @logout="onLogout" />
    <main class="main-panel" :class="mainPanelClass">
      <div class="main-panel__inner">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearAuth } from './api/auth'
import AppSidebar from './components/AppSidebar.vue'

const route = useRoute()
const router = useRouter()

const isAuthPage = computed(() => !!route.meta.public && !route.meta.demo)
const isStandalone = computed(() => !!route.meta.demo)

const chatRoutes = ['/chat', '/tutoring']
const mainPanelClass = computed(() =>
  chatRoutes.includes(route.path) ? 'main-panel--chat' : 'main-panel--page'
)

function onLogout() {
  clearAuth()
  router.push('/login')
}
</script>

<style>
@import './styles/minimal-theme.css';

body {
  margin: 0;
  background: #f7f8fa;
  color: #333338;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", "Source Han Sans SC", sans-serif;
}

.auth-shell {
  min-height: 100vh;
}

.standalone-shell {
  padding: 24px 20px 40px;
  max-width: 1200px;
  margin: 0 auto;
  box-sizing: border-box;
}
</style>
