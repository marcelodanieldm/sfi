<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import { useRouter } from 'vue-router'
import { useRoleplayStore } from '../stores/useRoleplayStore'

const props = defineProps({
  reportMarkdown: { type: String,  required: true },
  scenarioTitle:  { type: String,  default: '' },
  scenarioId:     { type: Number,  default: null },
  category:       { type: String,  default: '' },
  csrfToken:      { type: String,  default: '' },
})

const emit = defineEmits(['retry', 'choose-another'])

const router = useRouter()
const store  = useRoleplayStore()

const isRetrying = ref(false)

const parsed = computed(() => parseReport(props.reportMarkdown))

function parseReport(md) {
  if (!md) return { title: '', metaHtml: '', sections: [] }

  const lines    = md.split('\n')
  let title      = ''
  const metaLines = []
  const sections  = []
  let current    = null
  let parsingMeta = false

  for (const raw of lines) {
    const line = raw.trimEnd()

    if (line.startsWith('### ')) {
      title       = line.replace(/^#+\s+/, '').trim()
      parsingMeta = true
    } else if (line.startsWith('#### ')) {
      if (current) sections.push(current)
      parsingMeta = false
      current = {
        heading: line.replace(/^####\s+/, '').trim(),
        type:    inferType(line),
        content: [],
      }
    } else if (parsingMeta && line.trim()) {
      metaLines.push(line)
    } else if (current) {
      current.content.push(line)
    }
  }
  if (current) sections.push(current)

  return {
    title,
    metaHtml: metaLines.length ? marked.parse(metaLines.join('\n')) : '',
    sections:  sections.map(s => ({
      ...s,
      html:   s.type !== 'score' ? marked.parse(s.content.join('\n')) : '',
      scores: s.type === 'score' ? extractScores(s.content.join(' ')) : null,
    })),
  }
}

function inferType(line) {
  const h = line.toLowerCase()
  if (h.includes('positiv')    || h.includes('🟢')) return 'positive'
  if (h.includes('mejora')     || h.includes('🔴')) return 'improvement'
  if (h.includes('perfecta')   || h.includes('🚀')) return 'coach'
  if (h.includes('por qué')    || h.includes('💡') || h.includes('efectiva')) return 'why'
  if (h.includes('puntuación') || h.includes('📊')) return 'score'
  return 'default'
}

const fallbackHtml = computed(() =>
  parsed.value.sections.length === 0 ? marked.parse(props.reportMarkdown ?? '') : ''
)

function extractScores(text) {
  const rx  = /\*\*([^*]+)\*\*[:\s]+(\d+)\/(\d+)/g
  const out = []
  let m
  while ((m = rx.exec(text)) !== null) {
    out.push({ label: m[1].trim(), value: +m[2], max: +m[3] })
  }
  return out
}

function scoreBarClass(value, max) {
  const pct = value / max
  if (pct >= 0.8) return 'bg-emerald-500'
  if (pct >= 0.6) return 'bg-amber-400'
  return 'bg-red-400'
}

function scoreTextClass(value, max) {
  const pct = value / max
  if (pct >= 0.8) return 'text-[#34d399] font-bold'
  if (pct >= 0.6) return 'text-amber-400 font-bold'
  return 'text-red-400 font-bold'
}

async function retry() {
  const csrf = store.csrfToken || props.csrfToken
  if (!props.scenarioId || !csrf) {
    emit('retry')
    return
  }
  isRetrying.value = true
  try {
    const res = await fetch('/api/v1/roleplay/sessions/start/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body:    JSON.stringify({ scenario_id: props.scenarioId }),
    })
    if (!res.ok) throw new Error()
    const data = await res.json()

    emit('retry')

    if (router) {
      store.initSession(data.session_id, data.scenario, data.initial_bot_message)
      router.push(`/roleplay/${data.session_id}`)
    } else {
      window.location.href = `/roleplay/chat/${data.session_id}/`
    }
  } catch {
    emit('retry')
  } finally {
    isRetrying.value = false
  }
}

function chooseAnother() {
  emit('choose-another')
  store.resetSession()

  if (router) {
    const dest = props.category ? `/skills/${props.category}` : '/skills'
    router.push(dest)
  } else {
    const base = props.category ? `/roleplay/?category=${props.category}` : '/roleplay/'
    window.location.href = base
  }
}
</script>

<template>
  <div class="bg-[#0d1117] py-8 px-4" style="min-height:calc(100vh - 52px)">
    <div class="max-w-2xl mx-auto space-y-4">

      <!-- ── Header card (gradient stays) ──────────────────── -->
      <div class="bg-gradient-to-br from-indigo-700 to-violet-700 text-white rounded-2xl p-6 shadow-lg">
        <p class="text-xs uppercase tracking-widest text-indigo-200 mb-1" style="font-family:'JetBrains Mono',monospace">
          Informe Final · SkillsForIT
        </p>
        <h1 class="text-lg font-bold leading-snug mb-3">
          {{ parsed.title || '🎯 Informe de Feedback' }}
        </h1>
        <div
          class="text-sm text-indigo-100 [&_strong]:text-white [&_p]:mb-0"
          v-html="parsed.metaHtml"
        ></div>
      </div>

      <!-- ── Report sections ─────────────────────────────── -->
      <template v-for="section in parsed.sections" :key="section.heading">

        <!-- 🟢 Aspectos Positivos -->
        <section
          v-if="section.type === 'positive'"
          class="border-l-4 border-green-500 bg-[#1f2937] p-5 rounded-r-xl"
          aria-label="Aspectos positivos"
        >
          <div class="flex items-center gap-2 mb-3">
            <span class="text-lg leading-none" aria-hidden="true">🟢</span>
            <h2 class="text-sm font-semibold text-green-400">{{ section.heading }}</h2>
          </div>
          <div
            class="prose prose-sm prose-invert max-w-none prose-li:marker:text-green-500 prose-p:text-[#9ca3af] prose-li:text-[#9ca3af]"
            v-html="section.html"
          ></div>
        </section>

        <!-- 🔴 Áreas de Mejora -->
        <section
          v-else-if="section.type === 'improvement'"
          class="border-l-4 border-amber-500 bg-[#1f2937] p-5 rounded-r-xl"
          aria-label="Áreas de mejora"
        >
          <div class="flex items-center gap-2 mb-3">
            <span class="text-lg leading-none" aria-hidden="true">🔴</span>
            <h2 class="text-sm font-semibold text-amber-400">{{ section.heading }}</h2>
          </div>
          <div
            class="prose prose-sm prose-invert max-w-none prose-li:marker:text-amber-500 prose-p:text-[#9ca3af] prose-li:text-[#9ca3af]"
            v-html="section.html"
          ></div>
        </section>

        <!-- 🚀 La Respuesta Perfecta -->
        <section
          v-else-if="section.type === 'coach'"
          class="bg-[#0d1117] border border-[#374151] text-gray-200 p-6 rounded-xl"
          aria-label="Sugerencias del coach"
        >
          <div class="flex items-center gap-2 mb-4">
            <span class="text-lg leading-none" aria-hidden="true">🚀</span>
            <h2 class="text-sm font-semibold text-gray-100 tracking-wide">{{ section.heading }}</h2>
          </div>
          <div
            class="prose prose-sm prose-invert max-w-none prose-blockquote:border-[#34d399] prose-blockquote:text-[#34d399]/90 prose-p:text-[#9ca3af]"
            v-html="section.html"
          ></div>
        </section>

        <!-- 💡 ¿Por qué es más efectiva? -->
        <section
          v-else-if="section.type === 'why'"
          class="border-l-4 border-indigo-500 bg-[#1f2937] p-5 rounded-r-xl"
          aria-label="Por qué esta respuesta es más efectiva"
        >
          <div class="flex items-center gap-2 mb-3">
            <span class="text-lg leading-none" aria-hidden="true">💡</span>
            <h2 class="text-sm font-semibold text-indigo-400">{{ section.heading }}</h2>
          </div>
          <div
            class="prose prose-sm prose-invert max-w-none prose-p:text-[#9ca3af]"
            v-html="section.html"
          ></div>
        </section>

        <!-- 📊 Puntuación -->
        <section
          v-else-if="section.type === 'score' && section.scores?.length"
          class="bg-[#1f2937] rounded-xl border border-[#374151] p-5"
          aria-label="Puntuación"
        >
          <div class="flex items-center gap-2 mb-5">
            <span class="text-lg leading-none" aria-hidden="true">📊</span>
            <h2 class="text-sm font-semibold text-gray-100">{{ section.heading }}</h2>
          </div>
          <div class="space-y-4">
            <div v-for="score in section.scores" :key="score.label">
              <div class="flex justify-between items-baseline mb-1.5">
                <span class="text-sm text-[#9ca3af] font-medium">{{ score.label }}</span>
                <span :class="['text-sm tabular-nums', scoreTextClass(score.value, score.max)]">
                  {{ score.value }}/{{ score.max }}
                </span>
              </div>
              <div class="w-full bg-[#374151] rounded-full h-2 overflow-hidden" role="progressbar"
                :aria-valuenow="score.value" :aria-valuemax="score.max" :aria-label="score.label">
                <div
                  :class="['h-full rounded-full transition-all duration-700 ease-out', scoreBarClass(score.value, score.max)]"
                  :style="{ width: (score.value / score.max * 100) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </section>

        <!-- Genérica -->
        <section
          v-else
          class="bg-[#1f2937] rounded-xl border border-[#374151] p-5"
        >
          <div class="flex items-center gap-2 mb-3">
            <h2 class="text-sm font-semibold text-gray-100">{{ section.heading }}</h2>
          </div>
          <div class="prose prose-sm prose-invert max-w-none prose-p:text-[#9ca3af]" v-html="section.html"></div>
        </section>

      </template>

      <!-- Fallback -->
      <div
        v-if="parsed.sections.length === 0"
        class="bg-[#1f2937] rounded-xl border border-[#374151] p-6 prose prose-sm prose-invert max-w-none"
        v-html="fallbackHtml"
      ></div>

      <!-- ── Buttons ─────────────────────────────────────── -->
      <div class="flex flex-col sm:flex-row gap-3 pt-4 pb-10">
        <button
          :disabled="isRetrying"
          class="flex-1 py-3 px-5 bg-[#34d399] hover:bg-[#6ee7b7] active:bg-[#10b981] disabled:opacity-60 disabled:cursor-not-allowed text-[#0d1117] text-sm font-semibold rounded-xl transition-colors duration-150 flex items-center justify-center gap-2"
          style="font-family:'JetBrains Mono',monospace"
          @click="retry"
        >
          <svg
            v-if="isRetrying"
            class="w-4 h-4 animate-spin shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span>{{ isRetrying ? 'Iniciando...' : '🔄 Reintentar' }}</span>
        </button>

        <button
          class="flex-1 py-3 px-5 bg-[#1f2937] hover:bg-[#2d3748] border border-[#374151] hover:border-[#34d399]/40 text-gray-200 text-sm font-semibold rounded-xl transition-colors duration-150 flex items-center justify-center gap-2"
          style="font-family:'JetBrains Mono',monospace"
          @click="chooseAnother"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"/>
          </svg>
          Explorar otras habilidades
        </button>
      </div>

    </div>
  </div>
</template>
