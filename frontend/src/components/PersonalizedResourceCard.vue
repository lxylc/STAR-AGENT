<template>
  <ul v-if="items.length" class="res-list">
    <li
      v-for="row in items"
      :key="row.id"
      class="res-item"
      @click="$emit('open', row)"
    >
      <div class="res-head">
        <span class="res-title">{{ row.title }}</span>
        <div class="res-tags">
          <el-tag v-if="statusLabel(row)" size="small" :type="statusTagType(row)" effect="plain">
            {{ statusLabel(row) }}
          </el-tag>
          <el-tag size="small" :type="tagType(row.priority_tier)" effect="plain">
            {{ row.priority_label || '学情推荐' }}
          </el-tag>
        </div>
      </div>
      <p class="res-meta">
        <span v-if="row.module_name">{{ row.module_name }}</span>
        <span v-if="row.knowledgePoint"> · {{ row.knowledgePoint }}</span>
      </p>
      <p v-if="row.recommend_reason" class="res-reason">{{ row.recommend_reason }}</p>
      <button
        v-if="showMarkViewed && !statusLabel(row)"
        type="button"
        class="mark-btn"
        @click.stop="$emit('mark-viewed', row)"
      >
        标记已阅
      </button>
      <button
        v-if="showCopy && row.content?.includes('```')"
        type="button"
        class="copy-btn"
        @click.stop="$emit('copy', row.content)"
      >
        复制代码
      </button>
    </li>
  </ul>
  <div v-else class="empty-hint">暂无资源</div>
</template>

<script setup>
const props = defineProps({
  items: { type: Array, default: () => [] },
  showCopy: Boolean,
  showMarkViewed: Boolean,
  statusMap: { type: Object, default: () => ({}) }
})

defineEmits(['open', 'copy', 'mark-viewed'])

function tagType(tier) {
  if (tier === 'eval') return 'danger'
  if (tier === 'ai') return 'primary'
  if (tier === 'extend') return 'info'
  return 'warning'
}

function resourceStatus(row) {
  const id = row?.id
  return id ? props.statusMap[String(id)] : null
}

function statusLabel(row) {
  const st = resourceStatus(row)?.status
  if (st === 'completed') {
    const score = resourceStatus(row)?.score
    return score != null ? `已完成 · ${score}分` : '已完成'
  }
  if (st === 'viewed') return '已阅'
  return ''
}

function statusTagType(row) {
  const st = resourceStatus(row)?.status
  if (st === 'completed') return 'success'
  if (st === 'viewed') return 'info'
  return 'info'
}
</script>

<style scoped>
.res-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.res-item {
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.res-item:hover {
  border-color: #409eff;
}
.res-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.res-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
}
.res-title {
  font-weight: 500;
  color: #303133;
  flex: 1;
  min-width: 0;
  line-height: 1.4;
}
.res-meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: #909399;
}
.res-reason {
  margin: 6px 0 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
}
.copy-btn,
.mark-btn {
  margin-top: 8px;
  margin-right: 12px;
  font-size: 12px;
  color: #409eff;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.mark-btn {
  color: #67c23a;
}
.empty-hint {
  color: #909399;
  padding: 24px 0;
  text-align: center;
}
</style>
