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

// ── Estado ────────────────────────────────────────────────────
const scenarios   = ref([])
const isLoading   = ref(true)
const error       = ref(null)
const startingId  = ref(null)

// Categoría activa: viene del router si está disponible, si no del prop
const activeCategory = computed(() =>
  route?.params?.category ?? props.category ?? ''
)

// ── Catálogo de categorías para los tabs ──────────────────────
const CATEGORIES = [
  { slug: '',                 label: 'Todas',              color: 'gray'    },
  { slug: 'communication',   label: 'Comunicación',        color: 'blue'    },
  { slug: 'leadership',      label: 'Liderazgo',           color: 'yellow'  },
  { slug: 'negotiation',     label: 'Negociación',         color: 'emerald' },
  { slug: 'critical-thinking', label: 'Pensamiento Crítico', color: 'purple'},
  { slug: 'innovation',      label: 'Innovación',          color: 'orange'  },
  { slug: 'career',          label: 'Carrera',             color: 'indigo'  },
]

const TAB_ACTIVE = {
  gray:    'bg-gray-800    text-white border-gray-800',
  blue:    'bg-blue-600    text-white border-blue-600',
  yellow:  'bg-yellow-500  text-white border-yellow-500',
  emerald: 'bg-emerald-600 text-white border-emerald-600',
  purple:  'bg-purple-600  text-white border-purple-600',
  orange:  'bg-orange-500  text-white border-orange-500',
  indigo:  'bg-indigo-600  text-white border-indigo-600',
}
const TAB_INACTIVE = {
  gray:    'bg-white text-gray-700 border-gray-200 hover:bg-gray-50',
  blue:    'bg-white text-blue-700 border-blue-100 hover:bg-blue-50',
  yellow:  'bg-white text-yellow-700 border-yellow-100 hover:bg-yellow-50',
  emerald: 'bg-white text-emerald-700 border-emerald-100 hover:bg-emerald-50',
  purple:  'bg-white text-purple-700 border-purple-100 hover:bg-purple-50',
  orange:  'bg-white text-orange-700 border-orange-100 hover:bg-orange-50',
  indigo:  'bg-white text-indigo-700 border-indigo-100 hover:bg-indigo-50',
}

const CATEGORY_LABELS = {
  'communication':     'Comunicación',
  'leadership':        'Liderazgo',
  'negotiation':       'Negociación',
  'critical-thinking': 'Pensamiento Crítico',
  'innovation':        'Innovación',
  'career':            'Carrera',
}

// ── Fetch de escenarios ───────────────────────────────────────
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

// ── Navegación entre categorías ───────────────────────────────
function selectCategory(slug) {
  if (router) {
    const dest = slug ? `/skills/${slug}` : '/skills'
    router.push(dest)
  } else {
    // standalone: recarga con query param
    const url = new URL(window.location.href)
    if (slug) url.searchParams.set('category', slug)
    else url.searchParams.delete('category')
    window.location.href = url.toString()
  }
}

// ── Iniciar simulación ────────────────────────────────────────
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
  <div class="min-h-screen bg-gray-50">

    <!-- ── Cabecera con título ────────────────────────────────── -->
    <div class="bg-white border-b border-gray-200 px-4 pt-8 pb-0">
      <div class="max-w-5xl mx-auto">
        <p class="text-xs font-semibold tracking-widest text-indigo-500 uppercase mb-1">
          Roleplay de Soft Skills
        </p>
        <h1 class="text-2xl font-bold text-gray-900 mb-5">
          {{ activeCategory ? (CATEGORY_LABELS[activeCategory] ?? 'Escenarios') : 'Todos los escenarios' }}
        </h1>

        <!-- ── Tabs de categoría (scroll horizontal en mobile) ── -->
        <div class="flex gap-2 overflow-x-auto pb-px scrollbar-hide -mx-4 px-4">
          <button
            v-for="cat in CATEGORIES"
            :key="cat.slug"
            class="flex-none text-xs font-semibold px-3.5 py-1.5 rounded-full border transition-all duration-150 whitespace-nowrap"
            :class="activeCategory === cat.slug
              ? TAB_ACTIVE[cat.color]
              : TAB_INACTIVE[cat.color]"
            @click="selectCategory(cat.slug)"
          >
            {{ cat.label }}
          </button>
        </div>

        <!-- Línea separadora bajo los tabs -->
        <div class="h-px bg-gray-200 mt-0 -mx-4"></div>
      </div>
    </div>

    <!-- ── Contenido ──────────────────────────────────────────── -->
    <div class="max-w-5xl mx-auto px-4 py-8">

      <!-- Subtítulo con conteo -->
      <p v-if="!isLoading && !error" class="text-gray-500 text-sm mb-6">
        {{ scenarios.length }} simulaciones disponibles
        <template v-if="activeCategory">
          en <strong class="text-gray-700">{{ CATEGORY_LABELS[activeCategory] }}</strong>
        </template>
        · Orden aleatorio en cada visita
      </p>

      <!-- Skeletons de carga -->
      <div v-if="isLoading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="n in 6"
          :key="n"
          class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 animate-pulse"
        >
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
          <div class="h-3 bg-gray-200 rounded w-full mb-2"></div>
          <div class="h-3 bg-gray-200 rounded w-4/5 mb-5"></div>
          <div class="flex gap-2 mb-5">
            <div class="h-5 bg-gray-200 rounded-full w-28"></div>
            <div class="h-5 bg-gray-200 rounded-full w-28"></div>
          </div>
          <div class="h-9 bg-gray-200 rounded-lg"></div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-center py-20">
        <p class="text-red-500 text-sm mb-4">{{ error }}</p>
        <button
          class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          @click="fetchScenarios"
        >
          Reintentar
        </button>
      </div>

      <!-- Sin resultados -->
      <div v-else-if="scenarios.length === 0" class="text-center py-20">
        <p class="text-gray-400 text-sm">No hay escenarios disponibles para esta categoría.</p>
      </div>

      <!-- Grid de tarjetas -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <article
          v-for="scenario in scenarios"
          :key="scenario.id"
          class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
        >
          <!-- Categoría badge -->
          <span class="self-start text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full mb-2 bg-indigo-50 text-indigo-700">
            {{ CATEGORY_LABELS[scenario.category] ?? scenario.category }}
          </span>

          <!-- Título -->
          <h2 class="text-base font-semibold text-gray-900 mb-2 leading-snug">
            {{ scenario.title }}
          </h2>

          <!-- Contexto (máx. 3 líneas) -->
          <p class="text-gray-500 text-sm leading-relaxed mb-4 flex-1 line-clamp-3">
            {{ scenario.context }}
          </p>

          <!-- Roles -->
          <div class="flex flex-wrap gap-2 mb-3">
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
              <svg class="w-3 h-3 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
              </svg>
              Vos: {{ scenario.user_role }}
            </span>
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
              <svg class="w-3 h-3 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"/>
              </svg>
              Bot: {{ scenario.bot_role }}
            </span>
          </div>

          <p class="text-xs text-gray-400 mb-4">{{ scenario.max_turns }} turnos de práctica</p>

          <!-- CTA -->
          <button
            :disabled="startingId === scenario.id"
            class="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 flex items-center justify-center gap-2"
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
