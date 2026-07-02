<script setup>
import { RouterLink } from 'vue-router'

const CATEGORIES = [
  {
    slug:        'communication',
    label:       'Comunicación',
    description: 'Presentá ideas con claridad, manejá conflictos y transmitís tu valor en cualquier contexto laboral.',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
    </svg>`,
    color: 'blue',
  },
  {
    slug:        'leadership',
    label:       'Liderazgo',
    description: 'Inspirá a tu equipo, tomá decisiones bajo presión y gestioná personas con empatía y autoridad.',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
    </svg>`,
    color: 'yellow',
  },
  {
    slug:        'negotiation',
    label:       'Negociación',
    description: 'Cerrá acuerdos favorables, manejá objeciones y defendé tu posición con argumentos sólidos.',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
    </svg>`,
    color: 'emerald',
  },
  {
    slug:        'critical-thinking',
    label:       'Pensamiento Crítico',
    description: 'Analizá problemas complejos, cuestioná supuestos y tomá decisiones basadas en datos y lógica.',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
    </svg>`,
    color: 'purple',
  },
  {
    slug:        'innovation',
    label:       'Innovación',
    description: 'Proponé soluciones creativas, liderá el cambio y convertí ideas disruptivas en resultados concretos.',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
    </svg>`,
    color: 'orange',
  },
  {
    slug:        'career',
    label:       'Desarrollo de Carrera',
    description: 'Posicionáte estratégicamente, negociá tu salario y construí una marca profesional memorable.',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
    </svg>`,
    color: 'indigo',
  },
]

const STATS = [
  {
    value: '5 min',
    label: 'por simulación',
    detail: 'Sesiones cortas y focalizadas que se adaptan a tu agenda',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>`,
  },
  {
    value: 'IA',
    label: 'como coach personal',
    detail: 'Feedback inmediato y personalizado generado por GPT-4',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
    </svg>`,
  },
  {
    value: '6',
    label: 'habilidades clave',
    detail: 'Las que más valoran los equipos de tech en procesos de selección',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
    </svg>`,
  },
  {
    value: '100%',
    label: 'empleabilidad',
    detail: 'Practicá los escenarios reales que enfrentarás en tu próximo trabajo',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
    </svg>`,
  },
]

const COLOR_MAP = {
  blue:    { bg: 'bg-blue-50',    icon: 'text-blue-600',   badge: 'bg-blue-100 text-blue-700',   ring: 'ring-blue-200'   },
  yellow:  { bg: 'bg-yellow-50',  icon: 'text-yellow-500', badge: 'bg-yellow-100 text-yellow-700', ring: 'ring-yellow-200' },
  emerald: { bg: 'bg-emerald-50', icon: 'text-emerald-600',badge: 'bg-emerald-100 text-emerald-700',ring:'ring-emerald-200'},
  purple:  { bg: 'bg-purple-50',  icon: 'text-purple-600', badge: 'bg-purple-100 text-purple-700', ring: 'ring-purple-200' },
  orange:  { bg: 'bg-orange-50',  icon: 'text-orange-500', badge: 'bg-orange-100 text-orange-700', ring: 'ring-orange-200' },
  indigo:  { bg: 'bg-indigo-50',  icon: 'text-indigo-600', badge: 'bg-indigo-100 text-indigo-700', ring: 'ring-indigo-200' },
}
</script>

<template>
  <div class="min-h-screen bg-white font-sans antialiased text-gray-900">

    <!-- ════════════════════════════════════════════════════════
         HERO
    ════════════════════════════════════════════════════════ -->
    <section class="relative overflow-hidden bg-gradient-to-br from-slate-900 via-indigo-950 to-blue-900 text-white">
      <!-- Noise texture overlay -->
      <div class="absolute inset-0 opacity-[0.03]"
           style="background-image: url('data:image/svg+xml,%3Csvg viewBox=%220 0 256 256%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.9%22 numOctaves=%224%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22/%3E%3C/svg%3E'); background-size: 200px;">
      </div>

      <!-- Glow circles decorativos -->
      <div class="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-indigo-600 opacity-10 blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-20 -left-20 w-[400px] h-[400px] rounded-full bg-blue-500 opacity-10 blur-3xl pointer-events-none"></div>

      <div class="relative max-w-5xl mx-auto px-6 py-24 sm:py-32 text-center">

        <!-- Badge -->
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/10 border border-white/20 text-sm text-blue-200 mb-8 backdrop-blur-sm">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          Simulaciones de IA para profesionales de tech
        </div>

        <!-- Headline -->
        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight tracking-tight mb-6">
          Dominá las Soft Skills<br>
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-indigo-300">
            que el mercado tech exige
          </span>
        </h1>

        <!-- Subtítulo -->
        <p class="text-lg sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed mb-10">
          Practicá comunicación, liderazgo y negociación en simulaciones realistas con IA.
          Recibí feedback instantáneo y mejorá las habilidades que te diferencian en entrevistas y equipos.
        </p>

        <!-- CTAs -->
        <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
          <RouterLink
            to="/skills"
            class="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 active:bg-indigo-600 text-white font-semibold text-base shadow-lg shadow-indigo-900/50 transition-all duration-200 hover:-translate-y-0.5"
          >
            Comenzar a Entrenar Gratis
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"/>
            </svg>
          </RouterLink>
          <a
            href="#categorias"
            class="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border border-white/25 hover:bg-white/10 text-white font-medium text-base transition-all duration-200"
            @click.prevent="$router.push({ hash: '#categorias' })"
          >
            Ver habilidades
          </a>
        </div>

        <!-- Social proof sutil -->
        <p class="mt-10 text-sm text-slate-500">
          Simulaciones diseñadas para devs, leads y profesionales IT que quieren crecer
        </p>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════════════
         STATS / BENEFICIOS
    ════════════════════════════════════════════════════════ -->
    <section class="bg-slate-50 border-b border-gray-200 py-12">
      <div class="max-w-5xl mx-auto px-6">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          <div
            v-for="stat in STATS"
            :key="stat.value"
            class="flex flex-col items-center text-center p-5 rounded-2xl bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow duration-200"
          >
            <!-- Ícono -->
            <div class="w-11 h-11 flex items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 mb-3">
              <span v-html="stat.icon" class="w-5 h-5 [&>svg]:w-5 [&>svg]:h-5"></span>
            </div>
            <!-- Valor -->
            <span class="text-2xl font-extrabold text-gray-900 leading-none">{{ stat.value }}</span>
            <span class="text-sm font-semibold text-indigo-600 mt-0.5">{{ stat.label }}</span>
            <!-- Detalle -->
            <p class="text-xs text-gray-500 mt-2 leading-relaxed">{{ stat.detail }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════════════
         CATEGORÍAS
    ════════════════════════════════════════════════════════ -->
    <section id="categorias" class="py-20 bg-white">
      <div class="max-w-5xl mx-auto px-6">

        <!-- Encabezado de sección -->
        <div class="text-center mb-14">
          <span class="inline-block px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-semibold uppercase tracking-wider mb-4">
            Habilidades disponibles
          </span>
          <h2 class="text-3xl sm:text-4xl font-bold text-gray-900 leading-tight">
            6 áreas que definen tu carrera tech
          </h2>
          <p class="mt-3 text-gray-500 text-base max-w-xl mx-auto">
            Cada categoría incluye escenarios reales diseñados para los desafíos que enfrentás día a día en equipos de tecnología.
          </p>
        </div>

        <!-- Grid de categorías -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <RouterLink
            v-for="cat in CATEGORIES"
            :key="cat.slug"
            :to="`/skills/${cat.slug}`"
            class="group flex flex-col p-6 rounded-2xl border border-gray-100 hover:border-gray-200 bg-white shadow-sm hover:shadow-md transition-all duration-200 hover:-translate-y-0.5"
          >
            <!-- Ícono coloreado -->
            <div
              class="w-12 h-12 flex items-center justify-center rounded-xl mb-4 ring-1 transition-colors duration-200"
              :class="[COLOR_MAP[cat.color].bg, COLOR_MAP[cat.color].icon, COLOR_MAP[cat.color].ring]"
            >
              <span v-html="cat.icon" class="w-6 h-6 [&>svg]:w-6 [&>svg]:h-6"></span>
            </div>

            <!-- Badge de categoría -->
            <span
              class="self-start text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full mb-2"
              :class="COLOR_MAP[cat.color].badge"
            >
              {{ cat.label }}
            </span>

            <!-- Descripción -->
            <p class="text-sm text-gray-600 leading-relaxed flex-1">{{ cat.description }}</p>

            <!-- Enlace sutil -->
            <div class="mt-4 flex items-center gap-1 text-sm font-medium text-indigo-600 group-hover:gap-2 transition-all duration-150">
              Explorar simulaciones
              <svg class="w-4 h-4 transition-transform duration-150 group-hover:translate-x-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"/>
              </svg>
            </div>
          </RouterLink>
        </div>

      </div>
    </section>

    <!-- ════════════════════════════════════════════════════════
         CTA FINAL
    ════════════════════════════════════════════════════════ -->
    <section class="bg-gradient-to-br from-indigo-600 to-blue-700 py-20 text-white text-center">
      <div class="max-w-2xl mx-auto px-6">
        <h2 class="text-3xl sm:text-4xl font-bold mb-4 leading-tight">
          Tu próxima oportunidad empieza<br>con la conversación correcta
        </h2>
        <p class="text-indigo-200 text-base mb-8 leading-relaxed">
          Cinco minutos de práctica hoy pueden ser la diferencia en tu próxima entrevista,
          reunión o negociación salarial.
        </p>
        <RouterLink
          to="/skills"
          class="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-white text-indigo-700 hover:bg-indigo-50 font-bold text-base shadow-xl shadow-indigo-900/30 transition-all duration-200 hover:-translate-y-0.5"
        >
          Empezar ahora — es gratis
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"/>
          </svg>
        </RouterLink>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════════════
         FOOTER mínimo
    ════════════════════════════════════════════════════════ -->
    <footer class="bg-slate-900 text-slate-500 text-sm text-center py-6">
      © {{ new Date().getFullYear() }} SkillsForIT · Todos los derechos reservados
    </footer>

  </div>
</template>
