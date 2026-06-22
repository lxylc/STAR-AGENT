<template>
  <div class="mermaid-wrap">
    <div v-if="imageUrl" class="diagram-image">
      <img :src="imageUrl" :alt="title" />
      <p class="img-caption">AI 生成概念图</p>
    </div>
    <div v-else ref="containerRef" class="mermaid-render" />
    <details v-if="source && !imageUrl" class="source-toggle">
      <summary>查看 Mermaid 源码</summary>
      <pre>{{ source }}</pre>
    </details>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  source: { type: String, default: '' },
  title: { type: String, default: '图解' },
  imageUrl: { type: String, default: '' }
})

const containerRef = ref(null)
let mermaidApi = null

async function render() {
  if (props.imageUrl || !props.source?.trim() || !containerRef.value) return
  if (!mermaidApi) {
    const mod = await import('mermaid')
    mermaidApi = mod.default
    mermaidApi.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' })
  }
  const id = `mmd-${Math.random().toString(36).slice(2)}`
  containerRef.value.innerHTML = ''
  try {
    const { svg } = await mermaidApi.render(id, props.source.trim())
    containerRef.value.innerHTML = svg
  } catch {
    containerRef.value.innerHTML = `<pre class="fallback">${props.source}</pre>`
  }
}

watch(
  () => [props.source, props.imageUrl],
  async () => {
    await nextTick()
    render()
  }
)

onMounted(render)
</script>

<style scoped>
.mermaid-wrap {
  width: 100%;
}
.diagram-image img {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}
.img-caption {
  margin: 6px 0 0;
  font-size: 12px;
  color: #909399;
}
.mermaid-render {
  overflow-x: auto;
  background: #fff;
  padding: 8px;
  border-radius: 8px;
}
.mermaid-render :deep(svg) {
  max-width: 100%;
}
.source-toggle {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.source-toggle pre {
  white-space: pre-wrap;
  font-size: 11px;
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
}
.fallback {
  white-space: pre-wrap;
  font-size: 12px;
}
</style>
