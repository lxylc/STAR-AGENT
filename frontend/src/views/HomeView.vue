<template>

  <div class="think-workspace">

    <AgentChatPanel

      ref="chatPanelRef"

      class="workspace-main"

      @selection-change="selectionText = $event"

      @related-update="relatedQuestions = $event"

    />

    <AuxInfoPanel

      :selection-text="selectionText"

      :related-questions="relatedQuestions"

      @pick-question="onPickQuestion"

    />

  </div>

</template>



<script setup>

import { ref, nextTick } from 'vue'

import { useRoute, useRouter } from 'vue-router'

import AgentChatPanel from '../components/AgentChatPanel.vue'

import AuxInfoPanel from '../components/AuxInfoPanel.vue'



const route = useRoute()

const router = useRouter()



const chatPanelRef = ref(null)

const selectionText = ref('')

const relatedQuestions = ref([])



async function onPickQuestion(q) {

  if (route.query.view === 'history') {

    await router.replace({ path: '/chat' })

  }

  await nextTick()

  chatPanelRef.value?.fillQuestion(q)

}

</script>



<style scoped>

.think-workspace {

  display: flex;

  flex: 1;

  min-width: 0;

  min-height: 0;

  height: 100%;

  width: 100%;

  background: var(--tp-bg, #fafafb);

  gap: 0;

}



.workspace-main {

  flex: 1;

  min-width: 0;

}

</style>

