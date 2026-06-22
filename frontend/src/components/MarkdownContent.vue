<template>
  <div class="markdown-wrap">
    <div v-if="showToggle" class="view-toolbar">
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="rendered">排版阅读</el-radio-button>
        <el-radio-button value="raw">原始文本</el-radio-button>
      </el-radio-group>
    </div>

    <div
      v-if="viewMode === 'rendered'"
      class="markdown-body"
      v-html="renderedHtml"
    />
    <pre v-else class="markdown-raw">{{ cleanedText }}</pre>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { cleanMarkdownContent, renderMarkdown } from '../utils/markdown'

const props = defineProps({
  content: { type: String, default: '' },
  showToggle: { type: Boolean, default: true }
})

const viewMode = ref('rendered')

const cleanedText = computed(() => cleanMarkdownContent(props.content))
const renderedHtml = computed(() => renderMarkdown(props.content))
</script>

<style scoped>
.markdown-wrap {
  margin-top: 12px;
}
.view-toolbar {
  margin-bottom: 12px;
}
.markdown-raw {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.6;
  background: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  max-height: 70vh;
  overflow: auto;
  margin: 0;
}
.markdown-body {
  font-size: 14px;
  line-height: 1.75;
  color: #303133;
  background: #fafbfc;
  padding: 16px 20px;
  border-radius: 8px;
  max-height: 70vh;
  overflow: auto;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 1.2em 0 0.6em;
  font-weight: 600;
  color: #1f2d3d;
  line-height: 1.4;
}
.markdown-body :deep(h1) { font-size: 1.35em; border-bottom: 1px solid #e4e7ed; padding-bottom: 0.3em; }
.markdown-body :deep(h2) { font-size: 1.2em; }
.markdown-body :deep(h3) { font-size: 1.08em; }
.markdown-body :deep(p) { margin: 0.6em 0; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.4em;
  margin: 0.5em 0;
}
.markdown-body :deep(li) { margin: 0.25em 0; }
.markdown-body :deep(blockquote) {
  margin: 0.8em 0;
  padding: 8px 14px;
  border-left: 4px solid #409eff;
  background: #ecf5ff;
  color: #606266;
}
.markdown-body :deep(code) {
  font-family: Consolas, 'Courier New', monospace;
  font-size: 0.92em;
  background: #eef1f6;
  padding: 2px 6px;
  border-radius: 4px;
}
.markdown-body :deep(pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 14px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.8em 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.8em 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 8px 10px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}
.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}
.markdown-body :deep(a:hover) {
  text-decoration: underline;
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #ebeef5;
  margin: 1.2em 0;
}
</style>
