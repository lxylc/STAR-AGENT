<template>
  <div class="bilibili-embed">
    <div class="video-frame">
      <iframe
        :src="embedSrc"
        scrolling="no"
        border="0"
        frameborder="no"
        framespacing="0"
        allowfullscreen
        title="B站视频讲解"
      />
    </div>
    <div v-if="video?.title" class="video-meta">
      <span class="video-title">{{ video.title }}</span>
      <span v-if="video.author" class="video-author">UP：{{ video.author }}</span>
      <a
        v-if="video.bvid"
        class="video-link"
        :href="bilibiliPageUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        在 B 站打开
      </a>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  video: {
    type: Object,
    required: true
  }
})

const embedSrc = computed(() => {
  const v = props.video || {}
  if (v.embed_url) return v.embed_url
  const bvid = v.bvid || ''
  const page = v.page || 1
  const t = v.start_sec ? `&t=${v.start_sec}` : ''
  return `//player.bilibili.com/player.html?bvid=${bvid}&page=${page}&high_quality=1&danmaku=0${t}`
})

const bilibiliPageUrl = computed(() => {
  const bvid = props.video?.bvid
  return bvid ? `https://www.bilibili.com/video/${bvid}` : 'https://www.bilibili.com'
})
</script>

<style scoped>
.bilibili-embed {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
}
.video-frame {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
}
.video-frame iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.video-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  font-size: 12px;
  color: #606266;
}
.video-title {
  font-weight: 600;
  color: #303133;
}
.video-author {
  color: #909399;
}
.video-link {
  margin-left: auto;
  color: #00a1d6;
  text-decoration: none;
}
.video-link:hover {
  text-decoration: underline;
}
</style>
