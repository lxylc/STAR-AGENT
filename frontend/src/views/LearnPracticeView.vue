<template>
  <div class="learn-page" v-loading="loading">
    <div class="learn-head">
      <el-button link type="primary" @click="goBack">← 返回画像</el-button>
      <h2 class="learn-title">能力训练</h2>
      <p v-if="meta.module_name" class="learn-sub">
        {{ meta.module_name }} · {{ meta.kp_name }}
        <el-tag size="small">{{ tagTypeLabel }}</el-tag>
        <span>{{ meta.tag_content }}</span>
      </p>
    </div>

    <el-card shadow="never">
      <template #header>训练题库</template>
      <el-empty v-if="!exercises.length" description="暂无匹配练习题" />
      <div v-else class="exercise-list">
        <div v-for="(ex, idx) in exercises" :key="ex.ex_id" class="exercise-card">
          <div class="ex-head">
            <span class="ex-no">第 {{ idx + 1 }} 题</span>
            <el-tag size="small" type="info">难度 {{ ex.difficulty }}</el-tag>
          </div>
          <p class="ex-content">{{ ex.content }}</p>
          <ul v-if="optionEntries(ex).length" class="ex-options">
            <li v-for="[key, val] in optionEntries(ex)" :key="key">
              <strong>{{ key }}.</strong> {{ val }}
            </li>
          </ul>
        </div>
      </div>
    </el-card>

    <div v-if="resources.length" class="learn-actions">
      <el-button @click="goTutorial">查看教程资源（{{ resources.length }}）</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTagNavigateData } from '../api/profileBuild'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const exercises = ref([])
const resources = ref([])
const meta = reactive({
  module_name: '',
  kp_name: '',
  tag_content: '',
  tag_type: '',
  tutorial_route: ''
})

const tagTypeLabel = computed(() => {
  const m = { weakness: '知识短板', code: '代码实操', practice: '练习频次' }
  return m[meta.tag_type] || '训练'
})

function optionEntries(ex) {
  const opts = ex.options
  if (!opts || typeof opts !== 'object') return []
  return Object.entries(opts)
}

function goBack() {
  router.push('/profile/view')
}

function goTutorial() {
  if (meta.tutorial_route) router.push(meta.tutorial_route)
}

async function load() {
  const { studentId, moduleId, tagType, tagContent } = route.query
  if (!studentId || !moduleId || !tagType) return
  loading.value = true
  try {
    const data = await getTagNavigateData({
      student_id: studentId,
      module_id: moduleId,
      tag_type: tagType,
      tag_content: tagContent || ''
    })
    exercises.value = data.training_exercises || []
    resources.value = data.learning_resources || []
    meta.module_name = data.module_name
    meta.kp_name = data.kp_name
    meta.tag_content = data.tag_content
    meta.tag_type = data.tag_type
    meta.tutorial_route = data.tutorial_route
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.learn-page {
  width: 100%;
  margin: 0 auto;
  padding: 0 16px 32px;
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
.exercise-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.exercise-card {
  padding: 14px 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.ex-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ex-no {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.ex-content {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
}
.ex-options {
  margin: 0;
  padding-left: 0;
  list-style: none;
}
.ex-options li {
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}
.learn-actions {
  margin-top: 16px;
}
</style>
