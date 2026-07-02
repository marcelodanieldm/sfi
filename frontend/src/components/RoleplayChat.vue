<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { useRoleplayStore } from '../stores/useRoleplayStore'
import EvaluationReport from './EvaluationReport.vue'

// ── Store ────────────────────────────────────────────────────
const store = useRoleplayStore()

// Estado reactivo del store (refs individuales que mantienen reactividad)
const { messages, isLoading, report, currentSession } = storeToRefs(store)

// Getters del store expuestos como computed locales
const isCompleted     = computed(() => store.isCompleted)
const progressPercent = computed(() => store.progressPercent)
const turnCount       = computed(() => store.turnCount)
const scenario        = computed(() => store.scenario)

// ── Hidratación en refresh directo (modo SPA) ────────────────
// Si el usuario llega directamente a /soft-skills/roleplay/:sessionId
// (p.ej. recargando la página), el store está vacío. Fetcheamos la sesión.
const route = useRoute()
onMounted(async () => {
  if (!store.currentSession && route?.params?.sessionId) {
    await store.fetchSession(route.params.sessionId)
  }
})

// ── Estado UI-local (no pertenece al store) ──────────────────
const userInput     = ref('')
const chatContainer = ref(null)   // ref al contenedor de scroll
const inputRef      = ref(null)   // ref al textarea

// ── Computed UI ──────────────────────────────────────────────
const canSend = computed(() =>
  userInput.value.trim().length > 0 && store.canSendMessage
)

// ── Auto-scroll al agregar mensajes ──────────────────────────
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

// ── Auto-resize del textarea ──────────────────────────────────
function autoResize(event) {
  const el = event.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

// ── Enter para enviar (Shift+Enter = nueva línea) ─────────────
function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ── Envío delegado al store ───────────────────────────────────
async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || !store.canSendMessage) return

  userInput.value = ''
  if (inputRef.value) inputRef.value.style.height = 'auto'

  // El store maneja el estado optimista, la petición y la transición a 'completed'
  await store.sendMessage(text)
}
</script>

<template>
  <!-- Informe final: reemplaza el chat cuando la sesión se completa -->
  <EvaluationReport
    v-if="isCompleted && report"
    :report-markdown="report"
    :scenario-title="scenario?.title ?? ''"
    :scenario-id="scenario?.id ?? null"
    :category="scenario?.category ?? ''"
    :csrf-token="store.csrfToken"
  />

  <!-- Interfaz de chat activa -->
  <div v-else class="flex flex-col h-screen bg-gray-50 font-sans antialiased">

    <!-- ── Header fijo ─────────────────────────────────────── -->
    <header class="flex-none bg-white border-b border-gray-200 px-4 pt-3 pb-2.5 shadow-sm z-10">
      <div class="max-w-3xl mx-auto">

        <!-- Título + estado -->
        <div class="flex items-start justify-between gap-3 mb-2">
          <div class="min-w-0">
            <h1 class="text-sm font-semibold text-gray-900 leading-snug truncate">
              {{ scenario?.title ?? 'Roleplay' }}
            </h1>
            <p class="text-xs text-gray-400 mt-0.5">
              <span class="text-blue-600 font-medium">Vos: {{ scenario?.user_role }}</span>
              <span class="mx-1.5 text-gray-300">·</span>
              <span class="text-purple-600 font-medium">Bot: {{ scenario?.bot_role }}</span>
            </p>
          </div>

          <!-- Badge turno / estado -->
          <span
            class="flex-none text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap"
            :class="isCompleted ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'"
          >
            {{ isCompleted ? '✓ Completado' : `Turno ${turnCount} / ${store.maxTurns}` }}
          </span>
        </div>

        <!-- Barra de progreso de turnos -->
        <div
          class="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden"
          role="progressbar"
          :aria-valuenow="turnCount"
          :aria-valuemax="store.maxTurns"
        >
          <div
            class="h-full rounded-full transition-all duration-500 ease-out"
            :class="isCompleted ? 'bg-emerald-500' : 'bg-indigo-500'"
            :style="{ width: progressPercent + '%' }"
          ></div>
        </div>

      </div>
    </header>

    <!-- ── Área de mensajes (scroll independiente) ─────────── -->
    <div
      ref="chatContainer"
      class="flex-1 overflow-y-auto px-4 py-6"
    >
      <div class="max-w-3xl mx-auto space-y-5">

        <template v-for="(msg, i) in messages" :key="i">

          <!-- Mensaje del bot / personaje -->
          <div v-if="msg.role === 'assistant'" class="flex items-end gap-2.5">
            <div class="w-7 h-7 flex-none rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-[10px] font-bold uppercase">
              Bot
            </div>
            <div class="max-w-[75%] bg-white text-gray-800 rounded-2xl rounded-bl-none shadow-sm border border-gray-100 px-4 py-3 text-sm leading-relaxed">
              {{ msg.content }}
            </div>
          </div>

          <!-- Mensaje del usuario -->
          <div v-else-if="msg.role === 'user'" class="flex items-end gap-2.5 justify-end">
            <div class="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-br-none px-4 py-3 text-sm leading-relaxed">
              {{ msg.content }}
            </div>
            <div class="w-7 h-7 flex-none rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px] font-bold uppercase">
              Vos
            </div>
          </div>

          <!-- Error inline -->
          <div v-else-if="msg.role === 'error'" class="flex justify-center">
            <p class="text-xs text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              ⚠ {{ msg.content }}
            </p>
          </div>

        </template>

        <!-- Indicador de escritura -->
        <div v-if="isLoading" class="flex items-end gap-2.5">
          <div class="w-7 h-7 flex-none rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-[10px] font-bold uppercase">
            Bot
          </div>
          <div class="bg-white border border-gray-100 rounded-2xl rounded-bl-none shadow-sm px-4 py-3">
            <span class="flex gap-1 items-center h-4" aria-label="Escribiendo...">
              <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
              <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </span>
          </div>
        </div>

      </div>
    </div>

    <!-- ── Input fijo inferior ─────────────────────────────── -->
    <div class="flex-none bg-white border-t border-gray-200 px-4 py-3 z-10">
      <div class="max-w-3xl mx-auto">
        <div class="flex gap-2 items-end">

          <!-- Textarea auto-resize -->
          <textarea
            ref="inputRef"
            v-model="userInput"
            :disabled="isLoading || isCompleted"
            rows="1"
            placeholder="Escribí tu respuesta…"
            class="flex-1 resize-none rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm text-gray-900 placeholder-gray-400 leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-50 disabled:opacity-60 transition"
            style="min-height: 44px; max-height: 120px; overflow-y: auto;"
            @keydown="onKeydown"
            @input="autoResize"
          ></textarea>

          <!-- Botón de envío -->
          <button
            :disabled="!canSend"
            class="flex-none w-10 h-10 flex items-center justify-center rounded-xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors duration-150"
            aria-label="Enviar mensaje"
            @click="sendMessage"
          >
            <svg v-if="isLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
          </button>

        </div>

        <p class="text-xs text-gray-400 mt-1.5 text-right">
          Enter para enviar · Shift+Enter para nueva línea
        </p>
      </div>
    </div>

  </div>
</template>
