import { createApp }  from 'vue'
import { createPinia } from 'pinia'
import RoleplayChat    from '../components/RoleplayChat.vue'
import { useRoleplayStore } from '../stores/useRoleplayStore'
import '../style.css'

const el = document.getElementById('roleplay-chat-app')
if (el) {
  const scenario          = JSON.parse(document.getElementById('scenario-data').textContent)
  const initialBotMessage = el.dataset.initialBotMessage
  const sessionId         = el.dataset.sessionId
  const csrfToken         = el.dataset.csrf

  const app   = createApp(RoleplayChat)
  const pinia = createPinia()
  app.use(pinia)

  // Inicializar el store antes del mount para que los componentes
  // ya encuentren el estado listo en su primer render.
  const store = useRoleplayStore()
  store.init(csrfToken)
  store.initSession(sessionId, scenario, initialBotMessage)

  app.mount(el)
}
