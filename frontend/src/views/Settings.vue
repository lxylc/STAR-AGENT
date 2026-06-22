<template>

  <div class="settings-page">

    <el-card>

      <template #header>

        <div class="card-head">

          <span>个人设置</span>

          <el-button type="primary" link @click="$router.push('/profile/view')">查看画像</el-button>

        </div>

      </template>



      <div class="avatar-section">

        <div class="avatar-preview" :class="{ 'has-image': !!avatarUrl }">

          <img v-if="avatarUrl" :src="avatarUrl" alt="" class="avatar-img" />

          <span v-else class="avatar-initial">{{ displayInitial }}</span>

        </div>

        <div class="avatar-actions">

          <input ref="fileInputRef" type="file" accept="image/*" hidden @change="onAvatarChange" />

          <el-button size="small" @click="fileInputRef?.click()">更换头像</el-button>

          <el-button v-if="avatarUrl" size="small" link @click="removeAvatar">移除</el-button>

          <p class="avatar-hint">支持 JPG、PNG，建议小于 1MB</p>

        </div>

      </div>



      <p class="hint">在此编辑姓名、年级、专业与学习偏好；画像详情页同步展示，默认只读。</p>



      <el-descriptions :column="2" border class="preview-block">

        <el-descriptions-item label="姓名">{{ form.realName || '-' }}</el-descriptions-item>

        <el-descriptions-item label="年级">{{ form.grade || '-' }}</el-descriptions-item>

        <el-descriptions-item label="专业">{{ form.major || '-' }}</el-descriptions-item>

        <el-descriptions-item label="学习偏好">

          {{ formatLearnPreferences(form.learnPreferences) }}

        </el-descriptions-item>

      </el-descriptions>



      <el-divider content-position="left">编辑</el-divider>



      <el-form :model="form" label-width="100px">

        <el-form-item label="姓名">

          <el-input v-model="form.realName" />

        </el-form-item>

        <el-form-item label="年级">

          <el-select v-model="form.grade" placeholder="请选择" style="width: 100%">

            <el-option v-for="g in GRADE_OPTIONS" :key="g" :label="g" :value="g" />

          </el-select>

        </el-form-item>

        <el-form-item label="专业">

          <el-select v-model="form.major" placeholder="请选择" style="width: 100%">

            <el-option v-for="m in MAJOR_OPTIONS" :key="m" :label="m" :value="m" />

          </el-select>

        </el-form-item>

        <el-form-item label="学习偏好">

          <el-checkbox-group v-model="form.learnPreferences">

            <el-checkbox v-for="p in LEARN_PREF_OPTIONS" :key="p" :label="p" :value="p" />

          </el-checkbox-group>

          <p class="field-hint">可多选，用于个性化学习推荐</p>

        </el-form-item>

        <el-form-item>

          <el-button type="primary" :loading="loading" @click="save">保存</el-button>

          <el-button @click="$router.push('/profile/view')">返回画像</el-button>

        </el-form-item>

      </el-form>

    </el-card>

  </div>

</template>



<script setup>

import { computed, onMounted, reactive, ref } from 'vue'

import { ElMessage } from 'element-plus'

import { getMe, updateSettings, saveAuth, getStudentId, useStoredUser } from '../api/auth'

import {

  GRADE_OPTIONS,

  MAJOR_OPTIONS,

  LEARN_PREF_OPTIONS,

  formatLearnPreferences,

  parseLearnPreferences

} from '../constants/profileBasic'

import {

  getAvatarUrl,

  setAvatarUrl,

  readImageAsAvatar,

  getDisplayInitial

} from '../utils/avatarStorage'



const loading = ref(false)

const fileInputRef = ref(null)

const storedUser = useStoredUser()

const studentId = computed(() => getStudentId())

const avatarUrl = ref('')



const form = reactive({

  realName: '',

  grade: '',

  major: '',

  learnPreferences: []

})



const displayInitial = computed(() => getDisplayInitial({ ...storedUser.value, realName: form.realName }))



onMounted(async () => {

  const me = await getMe()

  form.realName = me.realName || ''

  form.grade = me.grade || ''

  form.major = me.major || ''

  form.learnPreferences = parseLearnPreferences(me.learnPreferences)

  avatarUrl.value = getAvatarUrl(studentId.value)

})



async function onAvatarChange(e) {

  const file = e.target.files?.[0]

  if (!file) return

  if (!file.type.startsWith('image/')) {

    ElMessage.warning('请选择图片文件')

    return

  }

  try {

    const dataUrl = await readImageAsAvatar(file)

    setAvatarUrl(studentId.value, dataUrl)

    avatarUrl.value = dataUrl

    ElMessage.success('头像已更新')

  } catch (err) {

    ElMessage.error(err.message || '头像上传失败')

  } finally {

    e.target.value = ''

  }

}



function removeAvatar() {

  setAvatarUrl(studentId.value, '')

  avatarUrl.value = ''

  ElMessage.success('已移除头像')

}



async function save() {

  loading.value = true

  try {

    const auth = await updateSettings({ ...form })

    saveAuth({ ...auth, token: localStorage.getItem('token') })

    ElMessage.success('已保存，画像页将同步更新')

  } finally {

    loading.value = false

  }

}

</script>



<style scoped>

.settings-page { width: 100%; }

.card-head { display: flex; justify-content: space-between; align-items: center; }

.hint { font-size: 13px; color: var(--tp-muted, #757582); margin: 0 0 16px; }

.preview-block { margin-bottom: 8px; }

.field-hint { margin: 6px 0 0; font-size: 12px; color: var(--tp-muted, #757582); }



.avatar-section {

  display: flex;

  align-items: center;

  gap: 20px;

  padding: 16px 0 20px;

  margin-bottom: 8px;

  border-bottom: 1px solid var(--tp-border, #eeeef2);

}



.avatar-preview {

  width: 72px;

  height: 72px;

  border-radius: 50%;

  flex-shrink: 0;

  background: var(--tp-hover, #f4f5f8);

  border: 1px solid var(--tp-border, #eeeef2);

  display: flex;

  align-items: center;

  justify-content: center;

  overflow: hidden;

}



.avatar-preview.has-image {

  background: #fff;

}



.avatar-img {

  width: 100%;

  height: 100%;

  object-fit: cover;

}



.avatar-initial {

  font-size: 24px;

  font-weight: 600;

  color: var(--tp-text, #333338);

}



.avatar-actions {

  display: flex;

  flex-direction: column;

  align-items: flex-start;

  gap: 6px;

}



.avatar-hint {

  margin: 0;

  font-size: 12px;

  color: var(--tp-muted, #757582);

}

</style>

