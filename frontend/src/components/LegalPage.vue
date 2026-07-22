<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  // 'terminos' | 'privacidad'
  type: {
    type: String,
    required: true,
    validator: (v) => ['terminos', 'privacidad'].includes(v),
  },
})

const TERMINOS_SECCIONES = [
  {
    titulo: 'Aceptación de los términos',
    cuerpo: 'Estos Términos y Condiciones regulan el acceso y uso de skillsforit.online y de todos los productos y servicios de SkillsForIT, incluyendo el Evaluador ATS, los eBooks de Soft Skills, MentorIA y el módulo de Roleplay de Soft Skills con IA. Al registrarte o usar cualquier funcionalidad de la plataforma, aceptás estos Términos en su totalidad.',
  },
  {
    titulo: 'Descripción del servicio',
    cuerpo: 'El módulo de Soft Skills con IA te permite practicar comunicación, liderazgo, negociación y otras habilidades mediante simulaciones (roleplay) generadas por inteligencia artificial, con feedback instantáneo. El servicio se presta "tal cual" y puede sufrir interrupciones por mantenimiento o causas fuera de nuestro control.',
  },
  {
    titulo: 'Cuenta de usuario',
    cuerpo: 'Para guardar tu progreso y personalizar los escenarios es necesario contar con una cuenta con datos veraces. Sos responsable de la confidencialidad de tus credenciales y de la actividad realizada desde tu cuenta.',
  },
  {
    titulo: 'Uso aceptable',
    cuerpo: 'No está permitido utilizar el servicio con fines ilícitos, intentar extraer o explotar el modelo de IA subyacente, ni compartir tus credenciales de acceso con terceros no autorizados. Nos reservamos el derecho de suspender cuentas que incumplan estas condiciones.',
  },
  {
    titulo: 'Contenido generado por Inteligencia Artificial',
    cuerpo: 'Los escenarios de roleplay y el feedback son generados total o parcialmente por modelos de IA (incluyendo modelos de OpenAI). Este contenido tiene fines orientativos y educativos, no constituye asesoramiento profesional, y puede contener imprecisiones.',
  },
  {
    titulo: 'Propiedad intelectual',
    cuerpo: 'El contenido, diseño, marca y tecnología de la plataforma son propiedad de SkillsForIT o de sus licenciantes. Se otorga al usuario una licencia limitada y personal de uso, quedando prohibida su explotación comercial sin autorización previa por escrito.',
  },
  {
    titulo: 'Limitación de responsabilidad',
    cuerpo: 'En la máxima medida permitida por la ley, SkillsForIT no será responsable por daños indirectos derivados del uso del servicio o de decisiones tomadas en base al feedback generado por IA.',
  },
  {
    titulo: 'Modificaciones',
    cuerpo: 'Podemos actualizar estos Términos o el servicio en cualquier momento. Los cambios relevantes se publicarán en esta página junto con la fecha de actualización.',
  },
  {
    titulo: 'Legislación aplicable',
    cuerpo: 'Estos Términos se rigen por las leyes aplicables en la República Argentina, sin perjuicio de los derechos que la normativa de protección al consumidor te otorgue en tu país de residencia.',
  },
  {
    titulo: 'Contacto',
    cuerpo: 'Ante cualquier consulta sobre estos Términos, escribinos a info@skillsforit.com.',
  },
]

const PRIVACIDAD_SECCIONES = [
  {
    titulo: 'Responsable del tratamiento',
    cuerpo: 'SkillsForIT es responsable del tratamiento de los datos personales recopilados a través de skillsforit.online y sus productos asociados. Ante cualquier consulta sobre privacidad, escribinos a info@skillsforit.com.',
  },
  {
    titulo: 'Datos que recopilamos',
    cuerpo: 'Datos de identificación y contacto (nombre, email, usuario), tus respuestas a los escenarios de roleplay y el feedback recibido, y datos técnicos y de uso (dirección IP, navegador, cookies). No almacenamos datos financieros: los pagos son procesados por Stripe, MercadoPago o Hotmart según el producto.',
  },
  {
    titulo: 'Finalidades del tratamiento',
    cuerpo: 'Utilizamos tus datos para prestar el servicio de práctica de soft skills, generar feedback personalizado, procesar pagos cuando corresponda, enviarte comunicaciones transaccionales y, con tu consentimiento, comunicaciones de marketing sobre nuestros productos.',
  },
  {
    titulo: 'Servicios de terceros',
    cuerpo: 'Para operar la plataforma compartimos datos, limitados a lo necesario, con OpenAI (generación de escenarios y feedback), Stripe y MercadoPago (pagos), Resend (emails transaccionales) y nuestro proveedor de hosting. No vendemos tus datos a terceros con fines publicitarios ajenos a SkillsForIT.',
  },
  {
    titulo: 'Privacidad de tus simulaciones',
    cuerpo: 'Tus sesiones de roleplay están vinculadas a tu cuenta y solo vos podés acceder a ellas. No las compartimos con otros usuarios ni las usamos para entrenar modelos de IA de terceros.',
  },
  {
    titulo: 'Plazo de conservación',
    cuerpo: 'Conservamos tus datos mientras tu cuenta esté activa y, luego de la baja, durante el plazo necesario para cumplir obligaciones legales, contables o fiscales.',
  },
  {
    titulo: 'Tus derechos',
    cuerpo: 'Podés solicitar acceso, rectificación, supresión, oposición, portabilidad o limitación del tratamiento de tus datos escribiendo a info@skillsforit.com.',
  },
  {
    titulo: 'Seguridad de la información',
    cuerpo: 'Aplicamos medidas técnicas y organizativas razonables (cifrado en tránsito, control de accesos, almacenamiento seguro de contraseñas) para proteger tus datos.',
  },
  {
    titulo: 'Cookies',
    cuerpo: 'Utilizamos cookies propias y de terceros para mantener tu sesión iniciada y analizar el uso de la plataforma. Podés configurarlas desde tu navegador.',
  },
  {
    titulo: 'Cambios a esta política',
    cuerpo: 'Podemos actualizar esta Política de Privacidad para reflejar cambios legales o técnicos. Publicaremos la versión vigente en esta página junto con la fecha de actualización.',
  },
  {
    titulo: 'Contacto',
    cuerpo: 'Para consultas o ejercicio de derechos sobre tus datos personales, escribinos a info@skillsforit.com.',
  },
]

const config = computed(() => {
  if (props.type === 'privacidad') {
    return {
      titulo: 'Política de Privacidad',
      secciones: PRIVACIDAD_SECCIONES,
      otraRuta: '/terminos',
      otraEtiqueta: 'Términos y Condiciones',
    }
  }
  return {
    titulo: 'Términos y Condiciones de Uso',
    secciones: TERMINOS_SECCIONES,
    otraRuta: '/privacidad',
    otraEtiqueta: 'Política de Privacidad',
  }
})
</script>

<template>
  <div class="min-h-screen bg-white text-slate-800">

    <nav class="sticky top-0 z-30 bg-slate-900 text-white">
      <div class="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
        <RouterLink to="/" class="font-bold tracking-tight">SkillsForIT</RouterLink>
        <div class="flex items-center gap-4 text-sm text-slate-300">
          <RouterLink :to="config.otraRuta" class="hover:text-white">{{ config.otraEtiqueta }}</RouterLink>
          <RouterLink to="/" class="hover:text-white">Volver al inicio</RouterLink>
        </div>
      </div>
    </nav>

    <main class="max-w-3xl mx-auto px-6 py-14">
      <p class="text-xs font-semibold uppercase tracking-widest text-indigo-600 mb-3">Legal</p>
      <h1 class="text-3xl sm:text-4xl font-bold mb-2">{{ config.titulo }}</h1>
      <p class="text-sm text-slate-400 mb-10">Última actualización: 21 de julio de 2026</p>

      <section
        v-for="(seccion, i) in config.secciones"
        :key="seccion.titulo"
        class="border border-slate-200 rounded-2xl p-6 sm:p-8 mb-5"
      >
        <h2 class="font-bold text-slate-900 mb-3 flex items-center gap-2">
          <span class="text-indigo-600 font-mono text-sm">{{ String(i + 1).padStart(2, '0') }}.</span>
          {{ seccion.titulo }}
        </h2>
        <p class="text-sm text-slate-600 leading-relaxed">{{ seccion.cuerpo }}</p>
      </section>
    </main>

    <footer class="bg-slate-900 text-slate-500 text-sm text-center py-6">
      <p>© {{ new Date().getFullYear() }} SkillsForIT · Todos los derechos reservados</p>
      <p class="mt-2 space-x-3">
        <RouterLink to="/terminos" class="hover:text-slate-300 underline">Términos y Condiciones</RouterLink>
        <span aria-hidden="true">·</span>
        <RouterLink to="/privacidad" class="hover:text-slate-300 underline">Política de Privacidad</RouterLink>
      </p>
    </footer>

  </div>
</template>
