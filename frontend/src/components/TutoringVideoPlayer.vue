<template>
  <div v-if="slides?.length" class="video-player">
    <div class="player-screen">
      <img v-if="currentSlide?.image_url" :src="currentSlide.image_url" class="slide-img" />
      <div v-else class="slide-placeholder">
        <h5>{{ currentSlide?.title }}</h5>
        <p>{{ currentSlide?.visual_hint || currentSlide?.narration }}</p>
      </div>
      <div class="slide-caption">{{ currentSlide?.title }}</div>
    </div>

    <div class="player-controls">
      <el-button size="small" :disabled="index <= 0" @click="prev">上一段</el-button>
      <el-button size="small" type="primary" @click="togglePlay">
        {{ playing ? '暂停' : '播放讲解' }}
      </el-button>
      <el-button size="small" :disabled="index >= slides.length - 1" @click="next">下一段</el-button>
      <span class="progress">{{ index + 1 }} / {{ slides.length }}</span>
    </div>

    <audio
      v-if="currentSlide?.audio_url"
      ref="audioRef"
      :src="currentSlide.audio_url"
      @ended="onAudioEnded"
    />

    <p v-if="!hasAnyAudio" class="tts-hint">
      未配置讯飞 TTS 时无语音文件；可点击「生成真实媒体」或启用浏览器朗读。
      <el-button v-if="canBrowserTts" size="small" link type="primary" @click="browserSpeak">
        浏览器朗读当前段
      </el-button>
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  slides: { type: Array, default: () => [] },
  title: { type: String, default: '讲解' }
})

const index = ref(0)
const playing = ref(false)
const audioRef = ref(null)

const currentSlide = computed(() => props.slides[index.value])
const hasAnyAudio = computed(() => props.slides.some((s) => s.audio_url))
const canBrowserTts = computed(() => typeof window !== 'undefined' && 'speechSynthesis' in window)

function prev() {
  stop()
  if (index.value > 0) index.value -= 1
}

function next() {
  stop()
  if (index.value < props.slides.length - 1) index.value += 1
}

function stop() {
  playing.value = false
  audioRef.value?.pause()
  window.speechSynthesis?.cancel()
}

async function togglePlay() {
  if (playing.value) {
    stop()
    return
  }
  playing.value = true
  const slide = currentSlide.value
  if (slide?.audio_url && audioRef.value) {
    audioRef.value.currentTime = 0
    try {
      await audioRef.value.play()
    } catch {
      browserSpeak()
    }
  } else {
    browserSpeak()
  }
}

function browserSpeak() {
  if (!canBrowserTts.value) return
  const text = currentSlide.value?.narration
  if (!text) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'zh-CN'
  u.onend = () => {
    if (playing.value && index.value < props.slides.length - 1) {
      index.value += 1
      togglePlay()
    } else {
      playing.value = false
    }
  }
  window.speechSynthesis.speak(u)
}

function onAudioEnded() {
  if (!playing.value) return
  if (index.value < props.slides.length - 1) {
    index.value += 1
    togglePlay()
  } else {
    playing.value = false
  }
}

watch(
  () => props.slides,
  () => {
    index.value = 0
    stop()
  }
)

onBeforeUnmount(stop)
</script>

<style scoped>
.video-player {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a2e;
}
.player-screen {
  position: relative;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.slide-img {
  max-width: 100%;
  max-height: 280px;
  border-radius: 6px;
}
.slide-placeholder {
  color: #e5eaf3;
  text-align: center;
  padding: 24px;
}
.slide-placeholder h5 {
  margin: 0 0 8px;
  font-size: 16px;
}
.slide-placeholder p {
  margin: 0;
  font-size: 13px;
  opacity: 0.85;
  line-height: 1.6;
}
.slide-caption {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  padding: 6px 12px;
  font-size: 13px;
}
.player-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #f5f7fa;
  flex-wrap: wrap;
}
.progress {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}
.tts-hint {
  margin: 0;
  padding: 8px 12px 12px;
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
}
</style>
