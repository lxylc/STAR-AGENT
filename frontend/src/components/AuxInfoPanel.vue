<template>

  <aside class="aux-panel">

    <section class="aux-card aux-card--explain">

      <h3 class="section-title">选区解释</h3>

      <div class="explain-scroll">
        <p v-if="!selectionText" class="empty-hint">

          在对话区拖选文字，此处将显示简要解释。

        </p>

        <template v-else>

          <blockquote class="selection-quote">{{ selectionText }}</blockquote>

          <p v-if="explaining" class="loading-hint">正在生成解释…</p>

          <p v-else-if="explainError" class="error-hint">{{ explainError }}</p>

          <div v-else-if="explanation" class="explanation-text">
            <MarkdownContent :content="explanation" :show-toggle="false" />
          </div>

        </template>
      </div>

    </section>



    <section class="aux-card aux-card--related">

      <h3 class="section-title">拓展问题</h3>

      <ul v-if="relatedQuestions.length" class="related-list">

        <li v-for="(q, idx) in relatedQuestions" :key="idx">

          <button type="button" class="related-item" @click="onPickQuestion(q)">

            <span class="related-dot" aria-hidden="true" />

            <span class="related-text">{{ q }}</span>

          </button>

        </li>

      </ul>

      <p v-else class="empty-hint">与当前对话相关的推荐问题将显示在这里。</p>

    </section>

  </aside>

</template>



<script setup>

import { ref, watch } from 'vue'

import { askQaQuestion } from '../api/profileBuild'

import { getStudentId } from '../api/auth'

import MarkdownContent from './MarkdownContent.vue'



const props = defineProps({
  selectionText: { type: String, default: '' },
  relatedQuestions: { type: Array, default: () => [] }
})

const emit = defineEmits(['pick-question'])



const studentId = getStudentId() || 1



const explaining = ref(false)

const explanation = ref('')

const explainError = ref('')

let explainTimer = null

let explainSeq = 0



function onPickQuestion(q) {

  if (!q?.trim()) return

  emit('pick-question', q.trim())

}



function looksLikeCode(text) {
  return /```|^\s*(def |class |for |while |import |from |print\(|if |else:|elif )/m.test(text)
}

function buildExplainPrompt(text) {
  if (looksLikeCode(text)) {
    return (
      '请解释以下 Python 代码的含义、逐行说明关键点，并给出可能的运行结果。'
      + '若需要补充示例，请用 markdown 代码块（```python）输出。面向初学者，3-6 句话：\n'
      + `\`\`\`python\n${text}\n\`\`\``
    )
  }
  return `请用 2～4 句话简要解释下面这段 Python 学习内容，面向初学者：\n「${text}」`
}

async function fetchExplanation(text) {

  const seq = ++explainSeq

  explaining.value = true

  explainError.value = ''

  explanation.value = ''

  try {

    const data = await askQaQuestion({

      student_id: studentId,

      question: buildExplainPrompt(text)

    })

    if (seq !== explainSeq) return

    const msgs = data.messages || []

    for (let i = msgs.length - 1; i >= 0; i--) {

      const m = msgs[i]

      if (m.role === 'assistant' && m.content) {

        explanation.value = m.content

        return

      }

    }

    explainError.value = '未能获取解释，请稍后重试'

  } catch (e) {

    if (seq !== explainSeq) return

    explainError.value = e.message || '解释生成失败'

  } finally {

    if (seq === explainSeq) explaining.value = false

  }

}



watch(

  () => props.selectionText,

  (text) => {

    clearTimeout(explainTimer)

    explanation.value = ''

    explainError.value = ''

    if (!text?.trim()) return

    explainTimer = setTimeout(() => fetchExplanation(text.trim()), 400)

  }

)

</script>



<style scoped>

.aux-panel {

  flex-shrink: 0;

  width: var(--aux-panel-width, 300px);

  display: flex;

  flex-direction: column;

  gap: 14px;

  padding: 20px 20px 20px 0;

  box-sizing: border-box;

  min-height: 0;

  height: 100%;

  overflow: hidden;

}



.aux-card {

  background: var(--tp-card, #fff);

  border: 1px solid var(--tp-border, #eeeef2);

  border-radius: var(--tp-radius-card, 16px);

  box-shadow: var(--tp-shadow, 0 2px 12px rgba(180, 190, 205, 0.1));

  padding: 18px 20px;

}



.aux-card--explain {

  flex: 1;

  min-height: 0;

  display: flex;

  flex-direction: column;

  overflow: hidden;

}



.aux-card--related {

  flex-shrink: 0;

  max-height: 42%;

  display: flex;

  flex-direction: column;

  overflow: hidden;

}



.explain-scroll {

  flex: 1;

  min-height: 0;

  overflow-y: auto;

  overflow-x: hidden;

  padding-right: 4px;

}



.explain-scroll::-webkit-scrollbar {

  width: 6px;

}



.explain-scroll::-webkit-scrollbar-thumb {

  background: #d4d7de;

  border-radius: 3px;

}



.explain-scroll::-webkit-scrollbar-thumb:hover {

  background: #b8bcc4;

}



.section-title {

  margin: 0 0 14px;

  font-size: 13px;

  font-weight: 600;

  color: var(--tp-text, #333338);

  letter-spacing: 0.02em;

  flex-shrink: 0;

}



.empty-hint,

.loading-hint,

.error-hint {

  margin: 0;

  font-size: 13px;

  line-height: 1.65;

  color: var(--tp-muted, #757582);

}



.error-hint {

  color: #c45656;

}



.selection-quote {

  margin: 0 0 12px;

  padding: 12px 14px;

  border-left: 3px solid var(--tp-tab-active, #c7edf0);

  background: var(--tp-bg, #fafafb);

  border-radius: 0 10px 10px 0;

  font-size: 13px;

  color: var(--tp-text, #333338);

  line-height: 1.55;

}



.explanation-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--tp-text, #333338);
}

.explanation-text :deep(.markdown-body) {
  background: transparent;
  padding: 0;
  max-height: none;
  font-size: 13px;
}

.explanation-text :deep(pre) {
  margin: 8px 0;
  font-size: 12px;
}



.related-list {

  margin: 0;

  padding: 0;

  list-style: none;

  display: flex;

  flex-direction: column;

  gap: 6px;

  flex: 1;

  min-height: 0;

  overflow-y: auto;

  padding-right: 2px;

}



.related-item {

  display: flex;

  align-items: flex-start;

  gap: 10px;

  width: 100%;

  text-align: left;

  padding: 12px 14px;

  border: 1px solid var(--tp-border, #eeeef2);

  border-radius: var(--tp-radius-btn, 10px);

  background: var(--tp-bg, #fafafb);

  color: var(--tp-text, #333338);

  font-size: 13px;

  line-height: 1.55;

  font-family: inherit;

  cursor: pointer;

  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;

}



.related-item:hover {

  background: var(--tp-tab-active, #c7edf0);

  border-color: var(--tp-tab-active-alt, #bde8eb);

  box-shadow: var(--tp-shadow, 0 2px 8px rgba(180, 190, 205, 0.08));

}



.related-dot {

  flex-shrink: 0;

  width: 6px;

  height: 6px;

  margin-top: 6px;

  border-radius: 50%;

  background: var(--tp-tab-active-alt, #bde8eb);

}



.related-text {

  flex: 1;

  min-width: 0;

}



@media (max-width: 900px) {

  .aux-panel {

    width: 100%;

    padding: 0 16px 16px;

    max-height: 40vh;

  }

  .aux-card--related {

    max-height: 36%;

  }

}

</style>

