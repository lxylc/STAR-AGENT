<template>
  <el-alert
    v-if="!loading && !profileCompleted"
    title="请先完成学习画像构建"
    description="完成画像构建后，方可使用本功能。点击下方按钮前往构建对话。"
    type="warning"
    :closable="false"
    show-icon
    class="profile-required-alert"
  >
    <template #default>
      <el-button type="primary" size="small" @click="$router.push('/profile/dialogue')">
        去构建画像
      </el-button>
    </template>
  </el-alert>
</template>

<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  profileCompleted: { type: Boolean, default: true }
})
</script>

<style scoped>
.profile-required-alert {
  margin-bottom: 16px;
}
.profile-required-alert :deep(.el-alert__content) {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>
