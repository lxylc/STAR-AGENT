<template>
  <div class="code-editor-wrap" :class="{ 'code-editor-wrap--readonly': readonly }">
    <div class="code-editor-toolbar">
      <span class="toolbar-lang">Python</span>
      <span v-if="!readonly" class="toolbar-hint">支持 Tab 缩进 · Ctrl+Enter 运行提示</span>
    </div>
    <div ref="editorHost" class="code-editor-host" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import { defaultKeymap, indentWithTab } from '@codemirror/commands'
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'

const props = defineProps({
  modelValue: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
  minHeight: { type: String, default: '220px' }
})

const emit = defineEmits(['update:modelValue'])

const editorHost = ref(null)
let view = null

function createExtensions() {
  const extensions = [
    lineNumbers(),
    highlightActiveLine(),
    highlightActiveLineGutter(),
    python(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    oneDark,
    keymap.of([...defaultKeymap, indentWithTab]),
    EditorView.lineWrapping,
    EditorView.theme({
      '&': { minHeight: props.minHeight, fontSize: '14px' },
      '.cm-scroller': { fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace" },
      '.cm-content': { padding: '12px 0' },
      '.cm-gutters': { border: 'none' }
    }),
    EditorView.updateListener.of((update) => {
      if (update.docChanged && !props.readonly) {
        emit('update:modelValue', update.state.doc.toString())
      }
    })
  ]
  if (props.readonly) {
    extensions.push(EditorState.readOnly.of(true))
  }
  return extensions
}

function initEditor() {
  if (!editorHost.value) return
  if (view) {
    view.destroy()
    view = null
  }
  view = new EditorView({
    state: EditorState.create({
      doc: props.modelValue || '',
      extensions: createExtensions()
    }),
    parent: editorHost.value
  })
}

function setDoc(text) {
  if (!view) return
  const cur = view.state.doc.toString()
  if (cur === text) return
  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: text || '' }
  })
}

watch(
  () => props.modelValue,
  (val) => setDoc(val ?? '')
)

watch(
  () => props.readonly,
  () => initEditor()
)

onMounted(initEditor)

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})
</script>

<style scoped>
.code-editor-wrap {
  border: 1px solid #30363d;
  border-radius: 8px;
  overflow: hidden;
  background: #282c34;
}
.code-editor-wrap--readonly {
  opacity: 0.92;
}
.code-editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #21252b;
  border-bottom: 1px solid #30363d;
  font-size: 12px;
}
.toolbar-lang {
  color: #61afef;
  font-weight: 600;
}
.toolbar-hint {
  color: #7f848e;
}
.code-editor-host {
  min-height: v-bind(minHeight);
}
.code-editor-host :deep(.cm-editor) {
  min-height: v-bind(minHeight);
}
.code-editor-host :deep(.cm-focused) {
  outline: none;
}
</style>
