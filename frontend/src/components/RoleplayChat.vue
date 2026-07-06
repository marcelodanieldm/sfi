<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { useRoleplayStore } from '../stores/useRoleplayStore'
import EvaluationReport from './EvaluationReport.vue'

const store = useRoleplayStore()

const { messages, isLoading, report, currentSession } = storeToRefs(store)

const isCompleted     = computed(() => store.isCompleted)
const progressPercent = computed(() => store.progressPercent)
const turnCount       = computed(() => store.turnCount)
const scenario        = computed(() => store.scenario)

const route = useRoute()
onMounted(async () => {
  if (!store.currentSession && route?.params?.sessionId) {
    await store.fetchSession(route.params.sessionId)
  }
})

const userInput     = ref('')
const chatContainer = ref(null)
const inputRef      = ref(null)

const canSend = computed(() =>
  userInput.value.trim().length > 0 && store.canSendMessage
)

watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

function scrollToBottom(behavior = 'smooth') {
  chatContainer.value?.scrollTo({
    top:      chatContainer.value.scrollHeight,
    behavior,
  })
}

function autoResize(event) {
  const el = event.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || !store.canSendMessage) return

  userInput.value = ''
  if (inputRef.value) inputRef.value.style.height = 'auto'

  await store.sendMessage(text)
}
</script>

<template>
  <!-- Informe final -->
  <EvaluationReport
    v-if="isCompleted && report"
    :report-markdown="report"
    :scenario-title="scenario?.title ?? ''"
    :scenario-id="scenario?.id ?? null"
    :category="scenario?.category ?? ''"
    :csrf-token="store.csrfToken"
  />

  <!-- Chat activo -->
  <div v-else class="flex flex-col bg-[#0d1117] font-sans antialiased" style="height:calc(100vh - 52px)">

    <!-- ── Scenario info bar ──────────────────────────────── -->
    <header class="flex-none bg-[#111827] border-b border-[#2d3748] px-4 pt-3 pb-2.5">
      <div class="max-w-3xl mx-auto">

        <div class="flex items-start justify-between gap-3 mb-2">
          <div class="min-w-0">
            <h1 class="text-sm font-semibold text-gray-100 leading-snug truncate">
              {{ scenario?.title ?? 'Roleplay' }}
            </h1>
            <p class="text-xs text-[#6b7280] mt-0.5">
              <span class="text-blue-400 font-medium">Vos: {{ scenario?.user_role }}</span>
              <span class="mx-1.5 text-[#374151]">·</span>
              <span class="text-purple-400 font-medium">Bot: {{ scenario?.bot_role }}</span>
            </p>
          </div>

          <span
            class="flex-none text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap"
            style="font-family:'JetBrains Mono',monospace"
            :class="isCompleted
              ? 'bg-[#34d399]/10 text-[#34d399] border border-[#34d399]/20'
              : 'bg-[#1f2937] text-[#9ca3af] border border-[#374151]'"
          >
            {{ isCompleted ? '✓ Completado' : `Turno ${turnCount} / ${store.maxTurns}` }}
          </span>
        </div>

        <!-- Progress bar -->
        <div
          class="w-full bg-[#374151] h-1 rounded-full overflow-hidden"
          role="progressbar"
          :aria-valuenow="turnCount"
          :aria-valuemax="store.maxTurns"
        >
          <div
            class="h-full rounded-full transition-all duration-500 ease-out"
            :class="isCompleted ? 'bg-[#34d399]' : 'bg-indigo-500'"
            :style="{ width: progressPercent + '%' }"
          ></div>
        </div>

      </div>
    </header>

    <!-- ── Messages ──────────────────────────────────────── -->
    <div
      ref="chatContainer"
      class="flex-1 overflow-y-auto px-4 py-5"
      style="scrollbar-width:thin;scrollbar-color:#374151 transparent"
    >
      <div class="max-w-3xl mx-auto space-y-4">

        <template v-for="(msg, i) in messages" :key="i">

          <!-- Bot -->
          <div v-if="msg.role === 'assistant'" class="flex items-end gap-2.5">
            <div class="w-7 h-7 flex-none rounded-full bg-[#2d1b69] text-purple-300 flex items-center justify-center text-[10px] font-bold uppercase" style="font-family:'JetBrains Mono',monospace">
              Bot
            </div>
            <div class="max-w-[75%] bg-[#1f2937] text-gray-200 rounded-2xl rounded-bl-none border border-[#374151] px-4 py-3 text-sm leading-relaxed">
              {{ msg.content }}
            </div>
          </div>

          <!-- User -->
          <div v-else-if="msg.role === 'user'" class="flex items-end gap-2.5 justify-end">
            <div class="max-w-[75%] bg-indigo-700 text-white rounded-2xl rounded-br-none px-4 py-3 text-sm leading-relaxed">
              {{ msg.content }}
            </div>
            <div class="w-7 h-7 flex-none rounded-full bg-[#1e3a5f] text-blue-300 flex items-center justify-center text-[10px] font-bold uppercase" style="font-family:'JetBrains Mono',monospace">
              Vos
            </div>
          </div>

          <!-- Error inline -->
          <div v-else-if="msg.role === 'error'" class="flex justify-center">
            <p class="text-xs text-red-400 bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">
              ⚠ {{ msg.content }}
            </p>
          </div>

        </template>

        <!-- Typing indicator -->
        <div v-if="isLoading" class="flex items-end gap-2.5">
          <div class="w-7 h-7 flex-none rounded-full bg-[#2d1b69] text-purple-300 flex items-center justify-center text-[10px] font-bold uppercase" style="font-family:'JetBrains Mono',monospace">
            Bot
          </div>
          <div class="bg-[#1f2937] border border-[#374151] rounded-2xl rounded-bl-none px-4 py-3">
            <span class="flex gap-1 items-center h-4" aria-label="Escribiendo...">
              <span class="w-1.5 h-1.5 bg-[#6b7280] rounded-full animate-bounce" style="animation-delay:0ms"></span>
              <span class="w-1.5 h-1.5 bg-[#6b7280] rounded-full animate-bounce" style="animation-delay:150ms"></span>
              <span class="w-1.5 h-1.5 bg-[#6b7280] rounded-full animate-bounce" style="animation-delay:300ms"></span>
            </span>
          </div>
        </div>

      </div>
    </div>

    <!-- ── Input ─────────────────────────────────────────── -->
    <div class="flex-none bg-[#111827] border-t border-[#2d3748] px-4 py-3">
      <div class="max-w-3xl mx-auto">
        <div class="flex gap-2 items-end">

          <textarea
            ref="inputRef"
            v-model="userInput"
            :disabled="isLoading || isCompleted"
            rows="1"
            placeholder="Escribí tu respuesta…"
            class="flex-1 resize-none rounded-xl border border-[#374151] bg-[#1f2937] px-3.5 py-2.5 text-sm text-gray-100 placeholder-[#6b7280] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#34d399]/50 focus:border-[#34d399]/50 disabled:opacity-50 disabled:cursor-not-allowed transition"
            style="min-height:44px;max-height:120px;overflow-y:auto"
            @keydown="onKeydown"
            @input="autoResize"
          ></textarea>

          <button
            :disabled="!canSend"
            class="flex-none w-10 h-10 flex items-center justify-center rounded-xl bg-[#34d399] hover:bg-[#6ee7b7] active:bg-[#10b981] disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150"
            aria-label="Enviar mensaje"
            @click="sendMessage"
          >
            <svg v-if="isLoading" class="w-4 h-4 animate-spin text-[#0d1117]" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <svg v-else class="w-4 h-4 text-[#0d1117]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
          </button>

        </div>

        <p class="text-xs text-[#6b7280] mt-1.5 text-right" style="font-family:'JetBrains Mono',monospace">
          Enter para enviar · Shift+Enter para nueva línea
        </p>
      </div>
    </div>

  </div>
</template>
