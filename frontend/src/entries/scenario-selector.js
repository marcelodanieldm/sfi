import { createApp } from 'vue'
import ScenarioSelector from '../components/ScenarioSelector.vue'
import '../style.css'

const el = document.getElementById('scenario-selector-app')
if (el) {
  createApp(ScenarioSelector, {
    category:   el.dataset.category  || '',
    csrfToken:  el.dataset.csrf      || '',
  }).mount(el)
}
