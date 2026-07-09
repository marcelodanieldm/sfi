<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRoleplayStore } from '../stores/useRoleplayStore'
import RoleSelector from './RoleSelector.vue'

const props = defineProps({
  csrfToken: { type: String, default: '' },
})

const emit = defineEmits(['scenario-selected'])

const router = useRouter()
const store  = useRoleplayStore()

const showRoleSelector = ref(true)
const isStarting      = ref(false)
const error           = ref(null)

onMounted(() => {
  showRoleSelector.value = true
})

/**
 * Cuando el usuario selecciona un rol:
 * 1. Llama a POST /api/v1/roleplay/sessions/start/ con rol_it_sesion
 * 2. OpenAI genera un escenario dinámico
 * 3. Navega a la sesión de chat
 */
async function onRoleSelected(rolItSesion) {
  isStarting.value = true
  error.value      = null
  showRoleSelector.value = false
  
  try {
    const csrf = store.csrfToken || props.csrfToken
    const res  = await fetch('/api/v1/roleplay/sessions/start/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body:    JSON.stringify({ rol_it_sesion: rolItSesion }),
    })
    
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.error || `Error ${res.status}`)
    }
    
    const data = await res.json()

    emit('scenario-selected', {
      sessionId:         data.session_id,
      scenario:          data.scenario,
      initialBotMessage: data.initial_bot_message,
    })

    // Guardar sesión en el store con rol
    store.initSession(
      data.session_id,
      data.scenario,
      data.initial_bot_message,
      rolItSesion
    )

    // Navegar al chat
    if (router) {
      await router.push(`/roleplay/${data.session_id}`)
    } else {
      window.location.href = `/roleplay/chat/${data.session_id}/`
    }
  } catch (err) {
    console.error('[ScenarioSelector] onRoleSelected error:', err)
    error.value = err.message || 'No se pudo iniciar la simulación. Intentá de nuevo.'
    showRoleSelector.value = true
  } finally {
    isStarting.value = false
  }
}
</script>

<template>
  <div class="scenario-selector">
    <!-- Modal Selector de Rol -->
    <RoleSelector 
      v-if="showRoleSelector"
      @role-selected="onRoleSelected"
      :disabled="isStarting"
    />

    <!-- Mensaje de error -->
    <div v-if="error" class="error-banner">
      <p class="error-text">{{ error }}</p>
    </div>

    <!-- Spinner mientras se genera el escenario -->
    <div v-if="isStarting" class="loading-container">
      <div class="spinner"></div>
      <p>Generando escenario personalizado...</p>
    </div>
  </div>
</template>

<style scoped>
.scenario-selector {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 2rem;
}

.error-banner {
  background-color: #fee2e2;
  border: 1px solid #fca5a5;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1rem;
  max-width: 500px;
}

.error-text {
  color: #dc2626;
  margin: 0;
  font-size: 0.95rem;
}

.loading-container {
  text-align: center;
  padding: 2rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: #fbbf24;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-container p {
  color: #9ca3af;
  margin: 0;
  font-size: 0.95rem;
}
</style>