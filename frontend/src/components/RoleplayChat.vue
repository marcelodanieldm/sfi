<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { useRoleplayStore } from '../stores/useRoleplayStore'
import EvaluationReport from './EvaluationReport.vue'
import RoleSelector from './RoleSelector.vue'

const store = useRoleplayStore()

const { messages, isLoading, report, currentSession } = storeToRefs(store)

const isCompleted     = computed(() => store.isCompleted)
const progressPercent = computed(() => store.progressPercent)
const turnCount       = computed(() => store.turnCount)
const scenario        = computed(() => store.scenario)

const route = useRoute()

// Mapa de roles IT para mostrar el label
const ROLES_IT_LABELS = {
  'frontend': 'Frontend Developer',
  'backend': 'Backend Developer',
  'fullstack': 'Fullstack Developer',
  'devops': 'DevOps Engineer',
  'data_engineer': 'Data Engineer',
  'qa': 'QA/Tester',
  'architect': 'Solutions Architect',
  'scrum_master': 'Scrum Master',
  'product_manager': 'Product Manager',
  'tech_lead': 'Tech Lead',
  'ml_engineer': 'ML/AI Engineer',
  'security': 'Security Engineer',
  'cloud_engineer': 'Cloud Engineer',
}

const showRoleSelector = ref(false)
const csrfToken = ref('')
const regenerateCount = ref(0)
const canRegenerate = ref(true)

onMounted(async () => {
  // Obtener CSRF token del DOM
  const csrfEl = document.querySelector('[data-csrf]')
  if (csrfEl) csrfToken.value = csrfEl.dataset.csrf
  
  if (!store.currentSession && route?.params?.sessionId) {
    await store.fetchSession(route.params.sessionId)
    // Forzar rerender después de que los datos se cargan
    await nextTick()
  }
})

// Watch para asegurar que se re-renderiza cuando cambia currentSession
watch(
  () => currentSession.value?.id,
  () => {
    // Cuando el ID de sesión cambia, forzamos un rerender
    nextTick()
  }
)

const userInput     = ref('')
const chatContainer = ref(null)
const inputRef      = ref(null)

// Computed que siempre lee el rol actual del store
const currentRolItSesion = computed(() => store.currentSession?.rol_it_sesion || '')

const canSend = computed(() =>
  userInput.value.trim().length > 0 && store.canSendMessage
)

const currentRoleLabel = computed(() =>
  currentRolItSesion.value ? ROLES_IT_LABELS[currentRolItSesion.value] || currentRolItSesion.value : 'Sin rol asignado'
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

function onRoleSelected(newRole) {
  currentRolItSesion.value = newRole
  showRoleSelector.value = false
  
  // Mostrar notificación en el chat que el rol fue cambiado
  const roleLabel = ROLES_IT_LABELS[newRole] || newRole
  console.log(`Rol IT cambiado a: ${roleLabel}. Los próximos escenarios serán personalizados según este rol.`)
}

function handleBackToChat() {
  // Volver al chat ocultando el informe final
  isCompleted.value = false
}

async function regenerateScenario() {
  if (!canRegenerate.value) return
  
  const userConfirmed = confirm('¿Regenerar escenario? Se borrará el chat actual. Tienes ' + (3 - regenerateCount.value) + ' regeneraciones disponibles.')
  if (!userConfirmed) return
  
  try {
    await store.regenerateScenario()
    regenerateCount.value += 1
    canRegenerate.value = regenerateCount.value < 3
  } catch (err) {
    console.error('Error regenerando escenario:', err)
    alert('Error al regenerar el escenario. Intentá de nuevo.')
  }
}
</script>

<template>
  <!-- RoleSelector Modal -->
  <RoleSelector
    :is-open="showRoleSelector"
    :csrf-token="csrfToken"
    @role-selected="onRoleSelected"
    @close="showRoleSelector = false"
  />

  <!-- Informe final -->
  <EvaluationReport
    v-if="isCompleted && report"
    :report-markdown="report"
    :scenario-title="scenario?.title ?? ''"
    :scenario-id="scenario?.id ?? null"
    :category="scenario?.category ?? ''"
    :csrf-token="csrfToken"
    @back-to-chat="handleBackToChat"
  />

  <!-- Chat activo -->
  <div v-else class="flex flex-col bg-[#0d1117] font-sans antialiased" style="height:calc(100vh - 52px);height:calc(100dvh - 52px);min-height:0">

    <!-- ── Scenario info bar ──────────────────────────────── -->
    <header class="flex-none bg-[#111827] border-b border-[#2d3748] px-3 pt-2 pb-1.5 sm:px-4 sm:pt-2.5 sm:pb-2">
      <div class="max-w-3xl mx-auto">

        <div class="flex items-center justify-between gap-2 mb-1.5">
          <div class="min-w-0 flex-1">
            <h1 class="text-xs sm:text-sm font-semibold text-gray-100 leading-snug truncate">
              {{ scenario?.title ?? 'Roleplay' }}
            </h1>
            <p class="text-[11px] sm:text-xs text-[#6b7280] mt-0.5 truncate">
              <span class="text-blue-400 font-medium">{{ scenario?.user_role }}</span>
              <span class="mx-1 text-[#374151]">vs</span>
              <span class="text-purple-400 font-medium">{{ scenario?.bot_role }}</span>
            </p>
          </div>

          <span
            class="flex-none text-[11px] sm:text-xs font-medium px-2 py-1 rounded-full whitespace-nowrap"
            style="font-family:'JetBrains Mono',monospace"
            :class="isCompleted
              ? 'bg-[#34d399]/10 text-[#34d399] border border-[#34d399]/20'
              : 'bg-[#1f2937] text-[#9ca3af] border border-[#374151]'"
          >
            {{ isCompleted ? '✓ Listo' : `${turnCount}/${store.maxTurns}` }}
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

        <!-- Rol IT del usuario y acciones -->
        <div class="mt-2 pt-1.5 border-t border-[#2d3748] flex items-center justify-between gap-2">
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-[#34d399]" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H5a2 2 0 00-2 2v10a2 2 0 002 2h5m0 0h5a2 2 0 002-2v-10a2 2 0 00-2-2h-5m0 0V5a2 2 0 012-2h.217a2 2 0 011.738 1.032l2.583 5m0 0H7"/>
            </svg>
            <span class="text-[10px] sm:text-xs text-[#9ca3af] font-medium">Tu rol:</span>
            <span class="text-[10px] sm:text-xs font-semibold text-[#34d399]">{{ currentRoleLabel }}</span>
          </div>
          <div class="flex items-center gap-1">
            <!-- Botón Regenerar (solo antes de empezar) -->
            <button
              v-if="turnCount === 0 && !isCompleted && canRegenerate"
              @click="regenerateScenario"
              :disabled="isLoading"
              class="text-[10px] px-2 py-1 rounded border border-[#fbbf24] text-[#fbbf24] hover:bg-[#fbbf24]/10 disabled:opacity-50 transition-colors"
              title="Regenerar escenario (máx 3 veces)"
            >
              🔄 Regenerar ({{ 3 - regenerateCount }} disponibles)
            </button>
            <!-- Botón Cambiar Rol -->
            <button
              @click="showRoleSelector = true"
              class="text-[10px] px-2 py-1 rounded border border-[#374151] text-[#6b7280] hover:text-[#34d399] hover:border-[#34d399] transition-colors"
              title="Cambiar rol IT"
            >
              Cambiar
            </button>
          </div>
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
    <div class="flex-none bg-[#111827] border-t border-[#2d3748] px-3 py-2.5 sm:px-4 sm:py-3">
      <div class="max-w-3xl mx-auto">
        <div class="flex gap-2 items-end">

          <textarea
            ref="inputRef"
            v-model="userInput"
            :disabled="isLoading || isCompleted"
            rows="1"
            placeholder="Escribí tu respuesta…"
            class="flex-1 resize-none rounded-xl border border-[#374151] bg-[#1f2937] px-3 py-2.5 sm:px-3.5 text-sm text-gray-100 placeholder-[#6b7280] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#34d399]/50 focus:border-[#34d399]/50 disabled:opacity-50 disabled:cursor-not-allowed transition"
            style="min-height:44px;max-height:120px;overflow-y:auto;touch-action:manipulation"
            @keydown="onKeydown"
            @input="autoResize"
          ></textarea>

          <button
            :disabled="!canSend"
            class="flex-none w-11 h-11 flex items-center justify-center rounded-xl bg-[#34d399] hover:bg-[#6ee7b7] active:bg-[#10b981] disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150"
            style="touch-action:manipulation"
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

        <p class="hidden sm:block text-xs text-[#6b7280] mt-1.5 text-right" style="font-family:'JetBrains Mono',monospace">
          Enter para enviar · Shift+Enter para nueva línea
        </p>
      </div>
    </div>

  </div>
</template>
