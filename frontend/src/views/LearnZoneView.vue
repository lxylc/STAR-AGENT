<template>

  <div class="learn-page" v-loading="loading">

    <div class="learn-head">

      <el-button link type="primary" @click="goBack">← 返回画像</el-button>

      <h2 class="learn-title">知识点学习专区</h2>

      <p v-if="meta.module_name" class="learn-sub">

        {{ meta.module_name }} · {{ meta.kp_name }}

        <el-tag size="small" type="warning">{{ meta.tag_content }}</el-tag>

      </p>

    </div>



    <el-card shadow="never">

      <template #header>教程与学习资源</template>

      <el-empty v-if="!resources.length" description="暂无匹配资源，可前往「学习资源」生成讲义">

        <el-button type="primary" @click="$router.push('/resource')">去学习资源</el-button>

      </el-empty>

      <ul v-else class="resource-list">

        <li

          v-for="r in resources"

          :key="r.id"

          class="resource-item"

          @click="openResource(r)"

        >

          <el-tag size="small">{{ typeLabel(r.resource_type || r.resourceType) }}</el-tag>

          <span class="resource-title">{{ r.title }}</span>

          <span class="resource-kp">{{ r.knowledge_point || r.knowledgePoint }}</span>

          <el-icon class="resource-arrow"><ArrowRight /></el-icon>

        </li>

      </ul>

    </el-card>



    <div v-if="exercises.length" class="learn-actions">

      <el-button type="primary" @click="goPractice">进入能力训练（{{ exercises.length }} 题）</el-button>

    </div>



    <ResourceDetailDrawer v-model:visible="drawerVisible" :resource="current" />

  </div>

</template>



<script setup>

import { ref, reactive, onMounted } from 'vue'

import { useRoute, useRouter } from 'vue-router'

import { ElMessage } from 'element-plus'

import { ArrowRight } from '@element-plus/icons-vue'

import { getTagNavigateData } from '../api/profileBuild'

import { getResource } from '../api/resource'

import ResourceDetailDrawer from '../components/ResourceDetailDrawer.vue'



const route = useRoute()

const router = useRouter()

const loading = ref(false)

const resources = ref([])

const exercises = ref([])

const drawerVisible = ref(false)

const current = ref(null)

const meta = reactive({

  module_name: '',

  kp_name: '',

  tag_content: '',

  practice_route: ''

})



function typeLabel(t) {

  return { lecture: '讲义', exercise: '习题', courseware: '课件' }[t] || t

}



function normalizeResource(row) {

  if (!row) return null

  return {

    ...row,

    resourceType: row.resourceType || row.resource_type,

    knowledgePoint: row.knowledgePoint || row.knowledge_point,

    contentJson: row.contentJson || row.content_json

  }

}



function goBack() {

  router.push('/profile/view')

}



function goPractice() {

  if (meta.practice_route) router.push(meta.practice_route)

}



async function openResource(row) {

  try {

    const detail = await getResource(row.id)

    current.value = normalizeResource(detail)

    drawerVisible.value = true

  } catch {

    if (row.content) {

      current.value = normalizeResource(row)

      drawerVisible.value = true

    } else {

      ElMessage.warning('无法加载资源详情，请确认 Java 后端已启动')

    }

  }

}



async function load() {

  const { studentId, moduleId, tagType, tagContent, kpId } = route.query

  if (!studentId || !moduleId || !tagType) return

  loading.value = true

  try {

    const data = await getTagNavigateData({

      student_id: studentId,

      module_id: moduleId,

      tag_type: tagType,

      tag_content: tagContent || '',

      kp_id: kpId

    })

    resources.value = data.learning_resources || []

    exercises.value = data.training_exercises || []

    meta.module_name = data.module_name

    meta.kp_name = data.kp_name

    meta.tag_content = data.tag_content

    meta.practice_route = data.practice_route

  } finally {

    loading.value = false

  }

}



onMounted(load)

</script>



<style scoped>

.learn-page {

  width: 100%;

  padding: 0 0 32px;

}

.learn-head {

  margin-bottom: 20px;

}

.learn-title {

  margin: 8px 0 4px;

  font-size: 20px;

  font-weight: 600;

}

.learn-sub {

  margin: 0;

  font-size: 14px;

  color: #606266;

  display: flex;

  align-items: center;

  gap: 8px;

  flex-wrap: wrap;

}

.resource-list {

  list-style: none;

  margin: 0;

  padding: 0;

}

.resource-item {

  display: flex;

  align-items: center;

  gap: 10px;

  padding: 12px 8px;

  border-bottom: 1px solid #f0f2f5;

  cursor: pointer;

  transition: background 0.2s;

}

.resource-item:hover {

  background: #f5f7fa;

}

.resource-title {

  flex: 1;

  font-size: 14px;

  color: #303133;

}

.resource-kp {

  font-size: 12px;

  color: #909399;

}

.resource-arrow {

  color: #c0c4cc;

  font-size: 14px;

}

.learn-actions {

  margin-top: 16px;

}

</style>

