<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRoleplayStore } from '../stores/useRoleplayStore'

const props = defineProps({
  category:  { type: String, default: '' },
  csrfToken: { type: String, default: '' },
})

const emit = defineEmits(['scenario-selected'])

const router = useRouter()
const route  = useRoute()
const store  = useRoleplayStore()

const scenarios   = ref([])
const isLoading   = ref(true)
const error       = ref(null)
const startingId  = ref(null)

const activeCategory = computed(() =>
  route?.params?.category ?? props.category ?? ''
)

const CATEGORIES = [
  { slug: '',                   label: 'Todas'              },
  { slug: 'communication',      label: 'Comunicación'       },
  { slug: 'leadership',         label: 'Liderazgo'          },
  { slug: 'negotiation',        label: 'Negociación'        },
  { slug: 'critical-thinking',  label: 'Pensamiento Crítico'},
  { slug: 'innovation',         label: 'Innovación'         },
  { slug: 'career',             label: 'Carrera'            },
]

const CATEGORY_LABELS = {
  'communication':     'Comunicación',
  'leadership':        'Liderazgo',
  'negotiation':       'Negociación',
  'critical-thinking': 'Pensamiento Crítico',
  'innovation':        'Innovación',
  'career':            'Carrera',
}

onMounted(fetchScenarios)
watch(activeCategory, fetchScenarios)

async function fetchScenarios() {
  isLoading.value = true
  error.value     = null
  try {
    const cat = activeCategory.value
    const qs  = cat ? `?category=${encodeURIComponent(cat)}` : ''
    const res = await fetch(`/api/v1/roleplay/scenarios/${qs}`)
    if (!res.ok) throw new Error(`Error ${res.status}`)
    const data      = await res.json()
    scenarios.value = data.scenarios
  } catch (err) {
    error.value = 'No se pudieron cargar los escenarios. Intentá de nuevo.'
    console.error('[ScenarioSelector] fetch error:', err)
  } finally {
    isLoading.value = false
  }
}

function selectCategory(slug) {
  if (router) {
    router.push(slug ? `/skills/${slug}` : '/skills')
  } else {
    const url = new URL(window.location.href)
    if (slug) url.searchParams.set('category', slug)
    else url.searchParams.delete('category')
    window.location.href = url.toString()
  }
}

async function startSession(scenario) {
  startingId.value = scenario.id
  try {
    const csrf = store.csrfToken || props.csrfToken
    const res  = await fetch('/api/v1/roleplay/sessions/start/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body:    JSON.stringify({ scenario_id: scenario.id }),
    })
    if (!res.ok) throw new Error(`Error ${res.status}`)
    const data = await res.json()

    emit('scenario-selected', {
      sessionId:         data.session_id,
      scenario:          data.scenario,
      initialBotMessage: data.initial_bot_message,
    })

    if (router) {
      store.initSession(data.session_id, data.scenario, data.initial_bot_message)
      router.push(`/roleplay/${data.session_id}`)
    } else {
      window.location.href = `/roleplay/chat/${data.session_id}/`
    }
  } catch (err) {
    console.error('[ScenarioSelector] start error:', err)
    alert('No se pudo iniciar la simulación. Intentá de nuevo.')
  } finally {
    startingId.value = null
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-52px)] bg-[#0d1117] font-sans">

    <!-- ── Category tab bar (sticky under nav) ──────────────── -->
    <div class="bg-[#111827] border-b border-[#2d3748] px-4 py-2.5 sticky top-[52px] z-10">
      <div class="max-w-5xl mx-auto flex gap-2 overflow-x-auto -mx-4 px-4" style="scrollbar-width:none">
        <button
          v-for="cat in CATEGORIES"
          :key="cat.slug"
          class="flex-none text-xs font-semibold px-3.5 py-1.5 rounded-full border transition-all duration-150 whitespace-nowrap"
          :class="activeCategory === cat.slug
            ? 'bg-[#34d399] text-[#0d1117] border-[#34d399]'
            : 'bg-transparent text-[#9ca3af] border-[#374151] hover:border-[#34d399] hover:text-[#34d399]'"
          @click="selectCategory(cat.slug)"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- ── Content ───────────────────────────────────────────── -->
    <div class="max-w-5xl mx-auto px-4 py-6">

      <!-- Subtitle + count -->
      <p v-if="!isLoading && !error" class="text-[#6b7280] text-sm mb-6" style="font-family:'JetBrains Mono',monospace">
        {{ scenarios.length }} simulaciones disponibles
        <template v-if="activeCategory">
          · <span class="text-[#9ca3af]">{{ CATEGORY_LABELS[activeCategory] }}</span>
        </template>
      </p>

      <!-- Skeletons -->
      <div v-if="isLoading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="n in 6"
          :key="n"
          class="bg-[#1f2937] rounded-xl border border-[#374151] p-5 animate-pulse"
        >
          <div class="h-3 bg-[#374151] rounded w-1/3 mb-3"></div>
          <div class="h-4 bg-[#374151] rounded w-3/4 mb-3"></div>
          <div class="h-3 bg-[#374151] rounded w-full mb-2"></div>
          <div class="h-3 bg-[#374151] rounded w-4/5 mb-5"></div>
          <div class="flex gap-2 mb-5">
            <div class="h-5 bg-[#374151] rounded-full w-28"></div>
            <div class="h-5 bg-[#374151] rounded-full w-24"></div>
          </div>
          <div class="h-9 bg-[#374151] rounded-lg"></div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-20">
        <p class="text-red-400 text-sm mb-4" style="font-family:'JetBrains Mono',monospace">{{ error }}</p>
        <button
          class="px-4 py-2 bg-[#34d399] text-[#0d1117] text-sm font-semibold rounded-lg hover:bg-[#6ee7b7] transition-colors"
          style="font-family:'JetBrains Mono',monospace"
          @click="fetchScenarios"
        >
          Reintentar
        </button>
      </div>

      <!-- Sin resultados -->
      <div v-else-if="scenarios.length === 0" class="text-center py-20">
        <p class="text-[#6b7280] text-sm" style="font-family:'JetBrains Mono',monospace">No hay escenarios para esta categoría.</p>
      </div>

      <!-- Grid de tarjetas -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <article
          v-for="scenario in scenarios"
          :key="scenario.id"
          class="bg-[#1f2937] rounded-xl border border-[#374151] p-5 flex flex-col hover:border-[#34d399]/40 hover:-translate-y-0.5 transition-all duration-200"
        >
          <!-- Category badge -->
          <span class="self-start text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full mb-2 bg-[#111827] text-[#34d399] border border-[#34d399]/20" style="font-family:'JetBrains Mono',monospace">
            {{ CATEGORY_LABELS[scenario.category] ?? scenario.category }}
          </span>

          <!-- Title -->
          <h2 class="text-sm font-semibold text-gray-100 mb-2 leading-snug">
            {{ scenario.title }}
          </h2>

          <!-- Context -->
          <p class="text-[#9ca3af] text-xs leading-relaxed mb-4 flex-1 line-clamp-3">
            {{ scenario.context }}
          </p>

          <!-- Roles -->
          <div class="flex flex-wrap gap-2 mb-3">
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#1e3a5f] text-blue-300">
              <svg class="w-3 h-3 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
              </svg>
              Vos: {{ scenario.user_role }}
            </span>
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#2d1b69] text-purple-300">
              <svg class="w-3 h-3 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"/>
              </svg>
              Bot: {{ scenario.bot_role }}
            </span>
          </div>

          <p class="text-xs text-[#6b7280] mb-4" style="font-family:'JetBrains Mono',monospace">{{ scenario.max_turns }} turnos</p>

          <!-- CTA -->
          <button
            :disabled="startingId === scenario.id"
            class="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-[#0d1117] bg-[#34d399] hover:bg-[#6ee7b7] active:bg-[#10b981] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 flex items-center justify-center gap-2"
            style="font-family:'JetBrains Mono',monospace"
            @click="startSession(scenario)"
          >
            <svg
              v-if="startingId === scenario.id"
              class="w-4 h-4 animate-spin shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            {{ startingId === scenario.id ? 'Iniciando...' : 'Iniciar Simulación' }}
          </button>
        </article>
      </div>

    </div>
  </div>
</template>
