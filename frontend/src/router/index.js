import { createRouter, createWebHistory } from 'vue-router'

/**
 * Rutas del módulo Soft Skills.
 *
 * Base: /soft-skills/  (configurado en createWebHistory)
 * Django sirve la SPA shell para todas las subrutas via catch-all.
 *
 * Flujo normal:
 *   / → /skills → /skills/:category → (POST API) → /roleplay/:sessionId
 *
 * Todas las vistas usan lazy loading (import dinámico) para que el bundle
 * principal sea mínimo y cada chunk se cargue solo cuando se necesita.
 */
const routes = [
  {
    path: '/',
    name: 'landing',
    component: () => import('../components/LandingPage.vue'),
    meta: { title: 'Soft Skills con IA — SkillsForIT' },
  },
  {
    // Catálogo completo de las 6 habilidades (sin filtro de categoría)
    path: '/skills',
    name: 'skills-catalog',
    component: () => import('../components/ScenarioSelector.vue'),
    props: { category: '' },
    meta: { title: 'Catálogo de Habilidades — SkillsForIT' },
  },
  {
    // Catálogo filtrado por categoría
    path: '/skills/:category',
    name: 'skills-category',
    component: () => import('../components/ScenarioSelector.vue'),
    props: (route) => ({ category: route.params.category }),
    meta: { title: 'Escenarios — SkillsForIT' },
  },
  {
    // Sala de chat de la simulación activa
    path: '/roleplay/:sessionId',
    name: 'roleplay-chat',
    component: () => import('../components/RoleplayChat.vue'),
    props: true,
    meta: { title: 'Simulación — SkillsForIT' },
  },
  {
    // Cualquier ruta no reconocida vuelve a la landing
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory('/soft-skills/'),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    // Restaura posición al usar Back/Forward del browser
    if (savedPosition) return savedPosition
    // Navega a un anchor (#categorias, etc.)
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    // Por defecto: vuelve arriba del todo, sin animación para que sea inmediato
    return { top: 0, behavior: 'instant' }
  },
})

// Actualiza el <title> del documento al navegar
router.afterEach((to) => {
  if (to.meta?.title) document.title = to.meta.title
})

export default router
