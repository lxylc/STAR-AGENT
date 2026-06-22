<template>
  <div v-if="sections" class="exercise-structured">
    <div v-for="sec in sections" :key="sec.title" class="exercise-section">
      <h4 class="section-title">{{ sec.title }}</h4>
      <div v-for="item in sec.items" :key="item.no" class="question-card">
        <p class="question-text">{{ item.no }}. {{ item.question }}</p>
        <ul v-if="item.options?.length" class="option-list">
          <li v-for="(opt, idx) in item.options" :key="idx">{{ opt }}</li>
        </ul>
        <div v-if="item.answer" class="answer-block">
          <span class="label">参考答案：</span>{{ item.answer }}
        </div>
        <div v-if="item.analysis" class="analysis-block">
          <span class="label">解析：</span>{{ item.analysis }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { parseExerciseJson, formatExerciseForDisplay } from '../utils/markdown'

const props = defineProps({
  contentJson: { type: String, default: '' }
})

const sections = computed(() => {
  const parsed = parseExerciseJson(props.contentJson)
  return formatExerciseForDisplay(parsed)
})
</script>

<style scoped>
.exercise-structured {
  margin-bottom: 16px;
}
.exercise-section {
  margin-bottom: 20px;
}
.section-title {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.question-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.question-text {
  margin: 0 0 8px;
  line-height: 1.6;
  color: #303133;
}
.option-list {
  margin: 0 0 8px;
  padding-left: 1.2em;
  color: #606266;
}
.answer-block,
.analysis-block {
  font-size: 13px;
  line-height: 1.6;
  margin-top: 6px;
  padding: 6px 10px;
  border-radius: 6px;
}
.answer-block {
  background: #f0f9eb;
  color: #529b2e;
}
.analysis-block {
  background: #fdf6ec;
  color: #b88230;
}
.label {
  font-weight: 600;
}
</style>
