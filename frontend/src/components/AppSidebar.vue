<template>

  <aside class="sidebar">

    <router-link to="/profile/view" class="user-block">
      <div class="user-avatar" :class="{ 'has-image': !!avatarUrl }">
        <img v-if="avatarUrl" :src="avatarUrl" alt="" class="avatar-img" />
        <span v-else class="avatar-initial">{{ displayInitial }}</span>
      </div>
      <div class="user-info">
        <span class="user-name">{{ displayName }}</span>
      </div>
    </router-link>



    <nav class="nav-menu">

      <router-link

        v-for="item in navItems"

        :key="item.to"

        :to="item.to"

        class="nav-item"

        :class="{ active: isActive(item) }"

      >

        <span class="nav-icon" v-html="item.iconSvg" />

        <span class="nav-label">{{ item.label }}</span>

      </router-link>

    </nav>



    <div class="sidebar-foot">

      <button type="button" class="foot-btn" @click="emit('logout')">退出登录</button>

    </div>

  </aside>

</template>



<script setup>

import { computed } from 'vue'

import { useRoute } from 'vue-router'

import { useStoredUser, getStudentId } from '../api/auth'

import { useAvatarUrl, getDisplayInitial } from '../utils/avatarStorage'



const emit = defineEmits(['logout'])

const route = useRoute()

const storedUser = useStoredUser()

const studentId = computed(() => getStudentId())

const avatarUrl = useAvatarUrl(studentId)



const isAdmin = computed(() => storedUser.value?.role === 'admin')



const displayName = computed(() => {

  const u = storedUser.value

  return u?.realName || u?.username || '用户'

})



const displayInitial = computed(() => getDisplayInitial(storedUser.value))



const icon = {

  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z"/></svg>',

  history: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',

  wrong: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9l6 6M15 9l-6 6"/></svg>',

  exercise: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>',

  eval: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19h16M6 16l3-8 3 5 3-7 3 10"/></svg>',

  kb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 5h14v14H5zM9 9h6M9 13h6M9 17h4"/></svg>',

  profile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',

  admin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20a8 8 0 0 1 16 0"/></svg>'

}



const navItems = computed(() => {

  if (isAdmin.value) {

    return [

      {

        to: '/admin/students',

        label: '学生管理',

        iconSvg: icon.admin,

        match: ['/admin']

      }

    ]

  }

  return [

    { to: '/chat', label: '首页', iconSvg: icon.home, match: ['/chat', '/tutoring'], navKey: 'home' },
    { to: '/profile/view', label: '用户画像', iconSvg: icon.profile, match: ['/profile/view'], navKey: 'profile' },
    { to: '/history', label: '历史记录', iconSvg: icon.history, match: ['/history'], navKey: 'history' },

    { to: '/learn/wrong-review', label: '错题复习', iconSvg: icon.wrong, match: ['/learn/wrong-review'], navKey: 'wrong' },

    { to: '/learn/exercise-center', label: '习题中心', iconSvg: icon.exercise, match: ['/learn/exercise-center', '/learn/practice', '/learn/module-practice'], navKey: 'exercise' },

    { to: '/evaluation', label: '学习效果评估', iconSvg: icon.eval, match: ['/evaluation'], navKey: 'eval' },

    { to: '/resource/personalized', label: '学习资源', iconSvg: icon.kb, match: ['/resource', '/path'], navKey: 'kb' },

    { to: '/settings', label: '设置', iconSvg: icon.settings, match: ['/settings'], navKey: 'settings' }

  ]

})



function isActive(item) {

  const path = route.path

  const matched = item.match?.some((p) => path === p || path.startsWith(p + '/')) ?? false

  if (!matched) return false

  return true

}

</script>



<style scoped>

.sidebar {

  width: var(--sidebar-width, 220px);

  flex-shrink: 0;

  display: flex;

  flex-direction: column;

  padding: 20px 14px 16px;

  background: var(--tp-card, #fff);

  border-right: 1px solid var(--tp-divider, #e8e8ec);

  height: 100vh;

  overflow-y: auto;

  box-sizing: border-box;

}



.user-block {

  display: flex;

  align-items: center;

  gap: 12px;

  padding: 10px 10px 20px;

  margin-bottom: 8px;

  text-decoration: none;

  border-radius: var(--tp-radius-card, 14px);

  transition: background 0.15s;

}



.user-block:hover {

  background: var(--tp-hover, #f4f5f8);

}



.user-avatar {

  width: 40px;

  height: 40px;

  border-radius: 50%;

  flex-shrink: 0;

  background: var(--tp-hover, #f0f1f5);

  display: flex;

  align-items: center;

  justify-content: center;

  overflow: hidden;

  border: 1px solid var(--tp-border, #eeeef2);

}



.user-avatar.has-image {

  background: #fff;

}



.avatar-img {

  width: 100%;

  height: 100%;

  object-fit: cover;

}



.avatar-initial {

  font-size: 15px;

  font-weight: 600;

  color: var(--tp-text, #333338);

}



.user-info {

  min-width: 0;

  display: flex;

  flex-direction: column;

  gap: 2px;

}



.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--tp-text, #333338);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}



.nav-menu {

  display: flex;

  flex-direction: column;

  gap: 4px;

  flex: 1;

}



.nav-item {

  display: flex;

  align-items: center;

  gap: 10px;

  padding: 10px 12px;

  text-decoration: none;

  color: var(--tp-muted, #757582);

  font-size: 13px;

  border-radius: var(--tp-radius-btn, 10px);

  transition: background 0.15s, color 0.15s;

}



.nav-item:hover {

  background: var(--tp-hover, #f4f5f8);

  color: var(--tp-text, #333338);

}



.nav-item.active {

  background: var(--tp-tab-active, #c7edf0);

  color: var(--tp-text, #333338);

  font-weight: 500;

}



.nav-icon {

  width: 18px;

  height: 18px;

  flex-shrink: 0;

  display: flex;

  align-items: center;

  justify-content: center;

  color: inherit;

}



.nav-icon :deep(svg) {

  width: 18px;

  height: 18px;

}



.nav-label {

  line-height: 1.3;

}



.sidebar-foot {

  margin-top: auto;

  padding-top: 12px;

  border-top: 1px solid var(--tp-border, #eeeef2);

}



.foot-btn {

  width: 100%;

  padding: 8px 12px;

  font-size: 12px;

  color: var(--tp-muted, #757582);

  background: none;

  border: none;

  border-radius: var(--tp-radius-btn, 10px);

  text-align: left;

  cursor: pointer;

  font-family: inherit;

}



.foot-btn:hover {

  background: var(--tp-hover, #f4f5f8);

  color: var(--tp-text, #333338);

}

</style>

