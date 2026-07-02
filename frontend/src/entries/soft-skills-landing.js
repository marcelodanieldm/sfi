import { createApp } from 'vue'
import LandingPage from '../components/LandingPage.vue'
import '../style.css'

const el = document.getElementById('soft-skills-landing-app')
if (el) {
  createApp(LandingPage).mount(el)
}
