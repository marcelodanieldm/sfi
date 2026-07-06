import { createApp }  from 'vue'
import { createPinia } from 'pinia'
import ScenarioSelector from '../components/ScenarioSelector.vue'
import { useRoleplayStore } from '../stores/useRoleplayStore'
import '../style.css'

const el = document.getElementById('scenario-selector-app')
if (el) {
  const app   = createApp(ScenarioSelector, {
    category:  el.dataset.category || '',
    csrfToken: el.dataset.csrf     || '',
  })
  const pinia = createPinia()
  app.use(pinia)

  const store = useRoleplayStore(pinia)
  store.init(el.dataset.csrf || '')

  app.mount(el)
}
