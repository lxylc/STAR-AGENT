<template>
  <div v-if="displayPayload" class="tutoring-answer">
    <section v-if="displayPayload.text_answer" class="block answer-text">
      <h4 class="block-title">文字解答</h4>
      <MarkdownContent :content="displayPayload.text_answer" :show-toggle="false" />
    </section>

    <section v-if="displayPayload.diagram?.mermaid || displayPayload.diagram_image_url" class="block">
      <h4 class="block-title">{{ displayPayload.diagram?.title || '图解说明' }}</h4>
      <MermaidDiagram
        :source="displayPayload.diagram?.mermaid || ''"
        :title="displayPayload.diagram?.title"
        :image-url="displayPayload.diagram_image_url || displayPayload.diagram?.image_url || ''"
      />
    </section>

    <section v-if="displayPayload.bilibili_videos?.length" class="block">
      <h4 class="block-title">视频讲解</h4>
      <p v-if="displayPayload.bilibili_videos.length > 1" class="video-hint">
        根据你的问题推荐了 {{ displayPayload.bilibili_videos.length }} 条 B 站讲解视频
      </p>
      <div class="video-list">
        <BilibiliEmbed
          v-for="(item, i) in displayPayload.bilibili_videos"
          :key="item.bvid + '-' + i"
          :video="item"
          class="video-item"
        />
      </div>
    </section>

    <!-- 兼容旧版 AI 脚本式视频（历史消息） -->
    <section
      v-else-if="displayPayload.video_script?.sections?.length || displayPayload.video_slides?.length"
      class="block"
    >
      <div class="block-head">
        <h4 class="block-title">
          {{ displayPayload.video_script?.title || '短视频讲解' }}
          <el-tag size="small" type="info">{{ displayPayload.video_script?.duration_sec || 60 }} 秒</el-tag>
        </h4>
        <el-button
          v-if="!displayPayload.video_slides?.length && !mediaLoading"
          size="small"
          type="primary"
          plain
          @click="$emit('generate-media')"
        >
          生成真实图片/语音
        </el-button>
        <el-icon v-if="mediaLoading" class="is-loading"><Loading /></el-icon>
      </div>

      <TutoringVideoPlayer
        v-if="displayPayload.video_slides?.length"
        :slides="displayPayload.video_slides"
        :title="displayPayload.video_script?.title"
      />

      <el-timeline v-else>
        <el-timeline-item
          v-for="(sec, i) in displayPayload.video_script.sections"
          :key="i"
          :timestamp="sec.title"
        >
          <p><strong>旁白：</strong>{{ sec.narration }}</p>
          <p v-if="sec.visual_hint" class="visual-hint">画面：{{ sec.visual_hint }}</p>
        </el-timeline-item>
      </el-timeline>
    </section>

    <section v-if="displayPayload.related_kps?.length" class="block">
      <h4 class="block-title">相关知识点</h4>
      <el-tag v-for="kp in displayPayload.related_kps" :key="kp" size="small" class="kp-tag">{{ kp }}</el-tag>
    </section>

    <section v-if="displayPayload.follow_up_actions?.length" class="block actions">
      <h4 class="block-title">后续学习</h4>
      <el-button
        v-for="act in displayPayload.follow_up_actions"
        :key="act.action"
        size="small"
        @click="$emit('follow-up', act)"
      >
        {{ act.label }}
      </el-button>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import MarkdownContent from './MarkdownContent.vue'
import MermaidDiagram from './MermaidDiagram.vue'
import BilibiliEmbed from './BilibiliEmbed.vue'
import TutoringVideoPlayer from './TutoringVideoPlayer.vue'
import { normalizeTutoringPayload } from '../utils/tutoring'

const props = defineProps({
  payload: { type: Object, default: null },
  fallbackContent: { type: String, default: '' },
  mediaLoading: { type: Boolean, default: false }
})

const displayPayload = computed(() => {
  const normalized = normalizeTutoringPayload(props.payload)
  if (!normalized) return null
  if (!normalized.text_answer?.trim() && props.fallbackContent?.trim()) {
    return { ...normalized, text_answer: props.fallbackContent.trim() }
  }
  return normalized
})

defineEmits(['follow-up', 'generate-media'])
</script>

<style scoped>
.tutoring-answer {
  width: 100%;
}
.block {
  margin-bottom: 16px;
}
.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.block-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}
.answer-text :deep(.markdown-body) {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 16px 18px;
  font-size: 14px;
  line-height: 1.75;
  color: #303133;
}
.answer-text :deep(.markdown-body pre) {
  margin: 12px 0;
}
.block-head .block-title {
  margin-bottom: 0;
}
.video-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #909399;
}
.video-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.visual-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
}
.kp-tag {
  margin: 0 6px 6px 0;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
