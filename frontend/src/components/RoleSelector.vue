<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  csrfToken: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['role-selected', 'close'])

const roles = ref([])
const selectedRole = ref('')
const userPreferredRole = ref('')
const isLoading = ref(false)
const error = ref(null)

onMounted(async () => {
  await fetchAvailableRoles()
})

async function fetchAvailableRoles() {
  isLoading.value = true
  error.value = null
  try {
    const res = await fetch('/api/v1/roleplay/roles/')
    if (!res.ok) throw new Error(`Error ${res.status}`)
    const data = await res.json()
    roles.value = data.roles
    userPreferredRole.value = data.user_role || ''
    selectedRole.value = data.user_role || ''
  } catch (err) {
    console.error('[RoleSelector] fetch error:', err)
    error.value = 'No se pudieron cargar los roles. Intentá de nuevo.'
  } finally {
    isLoading.value = false
  }
}

async function handleConfirm() {
  if (!selectedRole.value) {
    error.value = 'Por favor selecciona un rol IT'
    return
  }

  // Si el rol no es el preferido del usuario, actualizar el perfil
  if (selectedRole.value !== userPreferredRole.value) {
    try {
      const csrf = props.csrfToken || document.querySelector('[data-csrf]')?.dataset.csrf || ''
      const res = await fetch('/api/v1/roleplay/profile/update-role/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf
        },
        body: JSON.stringify({ rol_it_preferido: selectedRole.value })
      })
      if (!res.ok) throw new Error(`Error ${res.status}`)
    } catch (err) {
      console.error('[RoleSelector] update role error:', err)
      error.value = 'Error al guardar el rol. Intentá de nuevo.'
      return
    }
  }

  emit('role-selected', selectedRole.value)
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <!-- Backdrop -->
  <transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="isOpen"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
      @click="handleClose"
    />
  </transition>

  <!-- Modal -->
  <transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="opacity-0 scale-95"
    enter-to-class="opacity-100 scale-100"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100 scale-100"
    leave-to-class="opacity-0 scale-95"
  >
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="handleClose"
    >
      <div class="bg-[#1f2937] border border-[#374151] rounded-xl shadow-xl w-full max-w-md">
        <!-- Header -->
        <div class="border-b border-[#374151] px-6 py-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-100">Selecciona tu rol en IT</h2>
          <button
            @click="handleClose"
            class="text-[#6b7280] hover:text-gray-100 transition-colors"
            aria-label="Cerrar"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="px-6 py-4">
          <p class="text-sm text-[#9ca3af] mb-4">
            Personaliza los escenarios y preguntas basados en tu rol profesional. Esto nos ayudará a darte feedback más relevante.
          </p>

          <!-- Error message -->
          <div v-if="error" class="mb-4 p-3 bg-red-950/50 border border-red-900/50 rounded-lg text-sm text-red-300">
            {{ error }}
          </div>

          <!-- Loading state -->
          <div v-if="isLoading" class="space-y-2">
            <div v-for="n in 5" :key="n" class="h-10 bg-[#111827] rounded-lg animate-pulse"/>
          </div>

          <!-- Roles grid -->
          <div v-else class="space-y-2 max-h-80 overflow-y-auto">
            <button
              v-for="role in roles"
              :key="role.value"
              @click="selectedRole = role.value"
              class="w-full px-4 py-3 text-left rounded-lg border-2 transition-all duration-200"
              :class="selectedRole === role.value
                ? 'bg-[#34d399]/10 border-[#34d399] text-[#34d399] font-medium'
                : 'bg-[#111827] border-[#374151] text-[#9ca3af] hover:border-[#34d399]/50 hover:text-gray-100'"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all"
                  :class="selectedRole === role.value
                    ? 'border-[#34d399] bg-[#34d399]'
                    : 'border-[#4b5563]'"
                >
                  <svg
                    v-if="selectedRole === role.value"
                    class="w-3 h-3 text-[#0d1117]"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                  </svg>
                </div>
                <span>{{ role.label }}</span>
              </div>
            </button>
          </div>
        </div>

        <!-- Footer -->
        <div class="border-t border-[#374151] px-6 py-4 flex gap-3">
          <button
            @click="handleClose"
            class="flex-1 px-4 py-2 rounded-lg border border-[#374151] text-sm font-medium text-[#9ca3af] hover:bg-[#111827] hover:text-gray-100 transition-colors"
          >
            Cancelar
          </button>
          <button
            @click="handleConfirm"
            :disabled="!selectedRole || isLoading"
            class="flex-1 px-4 py-2 rounded-lg bg-[#34d399] text-[#0d1117] text-sm font-semibold hover:bg-[#6ee7b7] active:bg-[#10b981] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
/* Smooth scrollbar for role list */
div::-webkit-scrollbar {
  width: 6px;
}

div::-webkit-scrollbar-track {
  background: transparent;
}

div::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 3px;
}

div::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}
</style>
