/**
 * useRoleplayStore — Estado global del módulo de Roleplay de Soft Skills.
 *
 * Gestiona el ciclo completo de una sesión:
 *   1. startNewSession(scenarioId)  → POST /api/v1/roleplay/sessions/start/
 *   2. sendMessage(text)            → POST /api/v1/roleplay/sessions/<id>/message/
 *   3. Transición automática a 'completed' cuando la API devuelve is_final=true.
 *
 * Nota: El backend es Django (no Express/Node). Los endpoints son los mismos
 * definidos en core/controllers/roleplay_controller.py.
 */

import { defineStore } from 'pinia'

// ── Tipos de mensaje (documentación interna) ─────────────────
// { role: 'user'|'assistant'|'informe'|'error', content: string }

export const useRoleplayStore = defineStore('roleplay', {

  // ── Estado ───────────────────────────────────────────────────
  state: () => ({
    /** Token CSRF de Django. Se inicializa desde el entry point via init(). */
    csrfToken: '',

    /**
     * Sesión activa.
     * @type {{ id: string, scenario: object, turn_count: number, status: string } | null}
     */
    currentSession: null,

    /**
     * Historial de mensajes del chat.
     * @type {Array<{ role: string, content: string }>}
     */
    messages: [],

    /**
     * Texto en Markdown del informe final generado por la IA.
     * Se popula cuando turn_count alcanza max_turns y is_final es true.
     * @type {string | null}
     */
    report: null,

    /** Bloquea la interfaz mientras hay una petición en vuelo. */
    isLoading: false,

    /** Último mensaje de error, o null si no hay error activo. */
    error: null,
  }),

  // ── Getters ──────────────────────────────────────────────────
  getters: {
    /** True si la sesión fue completada y el informe está disponible. */
    isCompleted: (state) => state.currentSession?.status === 'completed',

    /** True si se puede enviar un mensaje en este momento. */
    canSendMessage: (state) =>
      !state.isLoading && state.currentSession?.status === 'in_progress',

    /** Turno actual de la sesión. */
    turnCount: (state) => state.currentSession?.turn_count ?? 0,

    /** Máximo de turnos permitidos en la sesión. */
    maxTurns: (state) => state.currentSession?.scenario?.max_turns ?? 4,

    /**
     * Porcentaje de progreso (0–100) para la barra de progreso.
     * Nunca supera el 100%.
     */
    progressPercent: (state) => {
      const turns = state.currentSession?.turn_count ?? 0
      const max   = state.currentSession?.scenario?.max_turns ?? 4
      return Math.min(100, Math.round((turns / max) * 100))
    },

    /** Acceso directo al escenario de la sesión activa. */
    scenario: (state) => state.currentSession?.scenario ?? null,
  },

  // ── Acciones ─────────────────────────────────────────────────
  actions: {

    /**
     * Inicializa el store con el token CSRF de Django.
     * Llamar desde el entry point antes de montar la app.
     *
     * @param {string} csrfToken - Valor de {{ csrf_token }} del template Django.
     */
    init(csrfToken) {
      this.csrfToken = csrfToken
    },

    /**
     * Inicializa el store con una sesión ya existente (cargada desde Django).
     * Útil cuando el usuario llega a la página del chat via redirect
     * después de que Django creó la sesión.
     *
     * @param {string} sessionId         - UUID de la sesión.
     * @param {object} scenario          - Datos del escenario.
     * @param {string} initialBotMessage - Primer mensaje del personaje.
     */
    initSession(sessionId, scenario, initialBotMessage) {
      this.currentSession = {
        id:         sessionId,
        scenario,
        turn_count: 0,
        status:     'in_progress',
      }
      this.messages  = [{ role: 'assistant', content: initialBotMessage }]
      this.report    = null
      this.error     = null
      this.isLoading = false
    },

    /**
     * Crea una nueva sesión en la API y popula el estado inicial.
     * Usado cuando ScenarioSelector inicia una sesión sin recargar la página.
     *
     * @param {number} scenarioId - ID del escenario a simular.
     * @returns {Promise<object>}  Datos de la sesión creada { session_id, scenario, initial_bot_message }.
     * @throws {Error}            Si la API responde con un error.
     */
    async startNewSession(scenarioId) {
      this._reset()
      this.isLoading = true

      try {
        const res = await fetch('/api/v1/roleplay/sessions/start/', {
          method:  'POST',
          headers: this._headers(),
          body:    JSON.stringify({ scenario_id: scenarioId }),
        })
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.error || `Error ${res.status}`)
        }
        const data = await res.json()

        this.currentSession = {
          id:         data.session_id,
          scenario:   data.scenario,
          turn_count: 0,
          status:     'in_progress',
        }
        this.messages.push({ role: 'assistant', content: data.initial_bot_message })

        return data
      } catch (err) {
        this.error = err.message
        throw err
      } finally {
        this.isLoading = false
      }
    },

    /**
     * Envía un turno del usuario y procesa la respuesta de la IA.
     * Cuando turn_count alcanza max_turns, la API devuelve is_final=true
     * y el store transiciona automáticamente a status='completed'.
     *
     * @param {string} messageText - Texto del mensaje del usuario.
     * @returns {Promise<object>}   Respuesta de la API { bot_message, turn_count, is_final, informe_feedback }.
     * @throws {Error}             Si la API responde con un error.
     */
    async sendMessage(messageText) {
      const text = messageText?.trim()
      if (!text || !this.canSendMessage) return

      // Agrega el mensaje del usuario de forma optimista (antes de esperar la API)
      this.messages.push({ role: 'user', content: text })
      this.isLoading = true
      this.error     = null

      try {
        const res = await fetch(
          `/api/v1/roleplay/sessions/${this.currentSession.id}/message/`,
          {
            method:  'POST',
            headers: this._headers(),
            body:    JSON.stringify({ userMessage: text }),
          }
        )
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.error || `Error ${res.status}`)
        }
        const data = await res.json()

        // Actualiza el contador de turnos en la sesión
        this.currentSession.turn_count = data.turn_count

        if (data.is_final) {
          // ── Transición automática a 'completed' ───────────────
          this.currentSession.status = 'completed'
          this.report                = data.informe_feedback
          // El mensaje queda en el historial por si se necesita fuera del componente de chat
          this.messages.push({ role: 'informe', content: data.informe_feedback })
        } else {
          this.messages.push({ role: 'assistant', content: data.bot_message })
        }

        return data
      } catch (err) {
        this.error = err.message
        this.messages.push({ role: 'error', content: err.message })
        throw err
      } finally {
        this.isLoading = false
      }
    },

    /**
     * Rehidrata el store con los datos de una sesión existente.
     * Usado cuando el usuario refresca la página en /soft-skills/roleplay/:sessionId.
     *
     * @param {string} sessionId - UUID de la sesión a cargar.
     */
    async fetchSession(sessionId) {
      this.isLoading = true
      this.error     = null
      try {
        const res = await fetch(`/api/v1/roleplay/sessions/${sessionId}/`, {
          headers: { 'X-CSRFToken': this.csrfToken },
        })
        if (!res.ok) throw new Error(`Error ${res.status}`)
        const data = await res.json()

        this.currentSession = {
          id:         data.session_id,
          scenario:   data.scenario,
          turn_count: data.turn_count,
          status:     data.status,
        }
        this.messages = data.chat_history ?? []
        this.report   = data.informe_feedback ?? null
      } catch (err) {
        this.error = err.message
      } finally {
        this.isLoading = false
      }
    },

    /**
     * Limpia todo el estado para iniciar una nueva simulación.
     * Llamar antes de startNewSession() si se reutiliza la instancia del store.
     */
    resetSession() {
      this._reset()
    },

    // ── Helpers privados ────────────────────────────────────────

    /** Cabeceras comunes para todas las peticiones a la API de Django. */
    _headers() {
      return {
        'Content-Type': 'application/json',
        'X-CSRFToken':  this.csrfToken,
      }
    },

    /** Limpia el estado mutable de la sesión. */
    _reset() {
      this.currentSession = null
      this.messages       = []
      this.report         = null
      this.error          = null
      this.isLoading      = false
    },
  },
})
