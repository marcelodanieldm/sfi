import { createApp }   from 'vue'
import { createPinia } from 'pinia'
import router           from '../router/index.js'
import App              from '../App.vue'
import { useRoleplayStore } from '../stores/useRoleplayStore'
import '../style.css'

const el = document.getElementById('soft-skills-app')
if (el) {
  const app   = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)

  // El CSRF token se inyecta en el template Django como meta tag.
  // Lo inicializamos antes del primer render para que todos los componentes
  // que lean el store ya lo tengan disponible.
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ?? ''
  const store = useRoleplayStore()
  store.init(csrfToken)

  app.mount(el)
}
