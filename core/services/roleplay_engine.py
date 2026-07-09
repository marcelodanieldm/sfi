"""
RoleplayEngineService — Lógica de IA para el módulo de Roleplay de Soft Skills.
"""
from __future__ import annotations

import logging
from typing import TypedDict

import openai
from django.conf import settings

from core.models import RoleplaySession, SoftskillsScenario

logger = logging.getLogger(__name__)

_INFORME_TRIGGER = (
    '[El roleplay ha terminado. Sal de tu personaje y genera '
    'estrictamente el formato de Informe de Feedback de SkillsForIT]'
)


class TurnResult(TypedDict):
    bot_message: str
    turn_count: int
    is_final: bool
    informe_feedback: str | None


class RoleplayEngineService:
    """
    Encapsula la lógica de IA para sesiones de roleplay de soft skills.
    """

    def __init__(self):
        self._client = openai.OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))

    # ──────────────────────────────────────────────────────────────────
    #  Prompt de sistema
    # ──────────────────────────────────────────────────────────────────

    def _get_role_context(self, rol_it: str | None) -> str:
        """
        Genera contexto adicional basado en el rol IT del usuario.
        Personaliza el escenario para ser relevante a su rol específico.
        """
        if not rol_it:
            return ""
        
        # Mapeo de rol IT a contexto de aplicación profesional
        role_contexts = {
            'frontend': "El usuario trabaja como Frontend Developer. Personaliza el escenario considerando desafíos típicos de frontend: diseño responsivo, performance, compatibilidad entre navegadores, user experience, testing de UI, y colaboración con diseñadores.",
            'backend': "El usuario trabaja como Backend Developer. Personaliza el escenario considerando desafíos típicos de backend: escalabilidad, seguridad, manejo de bases de datos, APIs, testing, debugging en producción, y arquitectura de sistemas.",
            'fullstack': "El usuario trabaja como Fullstack Developer. Personaliza el escenario considerando su visión end-to-end: desde la experiencia del usuario hasta la infraestructura, integrando desafíos de frontend y backend.",
            'devops': "El usuario trabaja como DevOps Engineer. Personaliza el escenario considerando desafíos de DevOps: CI/CD, infraestructura como código, monitoreo, escalado, seguridad en deployment, y automatización.",
            'data_engineer': "El usuario trabaja como Data Engineer. Personaliza el escenario considerando desafíos de data: pipelines ETL, big data, calidad de datos, performance de queries, y manejo de grandes volúmenes.",
            'qa': "El usuario trabaja como QA/Tester. Personaliza el escenario considerando desafíos de testing: cobertura de tests, bugs difíciles de reproducir, automatización de tests, y comunicación con devs.",
            'architect': "El usuario trabaja como Solutions Architect. Personaliza el escenario considerando desafíos de arquitectura: decisiones de diseño, trade-offs, escalabilidad, tecnología y negocios.",
            'scrum_master': "El usuario trabaja como Scrum Master. Personaliza el escenario considerando desafíos de facilitación: conflictos en el equipo, impedimentos, retrospectivas, y manejo ágil.",
            'product_manager': "El usuario trabaja como Product Manager. Personaliza el escenario considerando desafíos de PM: priorización, comunicación entre equipos, roadmap, y toma de decisiones.",
            'tech_lead': "El usuario trabaja como Tech Lead. Personaliza el escenario considerando desafíos de liderazgo técnico: mentoring, decisiones técnicas, balance entre crecimiento del equipo y delivery.",
            'ml_engineer': "El usuario trabaja como ML/AI Engineer. Personaliza el escenario considerando desafíos de ML: datasets, training, validación, deployment de modelos, y ethics de IA.",
            'security': "El usuario trabaja como Security Engineer. Personaliza el escenario considerando desafíos de seguridad: vulnerabilidades, compliance, auditorías, y educación en seguridad.",
            'cloud_engineer': "El usuario trabaja como Cloud Engineer. Personaliza el escenario considerando desafíos de cloud: migrations, costos, compliance multi-cloud, y optimización.",
        }
        
        return role_contexts.get(rol_it, "")

    def generate_dynamic_scenario(self, rol_it: str) -> dict:
        """
        Genera un escenario de roleplay completamente nuevo basado en el rol IT.
        
        Retorna un diccionario con estructura:
        {
            'title': str,
            'context': str,
            'user_role': str,
            'bot_role': str,
            'initial_bot_message': str,
            'max_turns': int
        }
        """
        role_labels = dict(__import__('core.models', fromlist=['User']).User.ROLES_IT)
        rol_label = role_labels.get(rol_it, rol_it)

        prompt = f"""Genera un escenario de roleplay para entrenar soft skills de un profesional que trabaja como {rol_label}.

El escenario debe:
1. Ser realista y desafiante (no trivial)
2. Simular una situación profesional común que requiera habilidades blandas
3. Tener un conflicto o dilema que requiera comunicación, negociación o liderazgo
4. Ser completable en 4-5 turnos de conversación

Responde en EXACTAMENTE este formato JSON (sin markdown, sin código blocks):
{{"title": "Nombre corto del escenario", "context": "Descripción de la situación profesional (2-3 párrafos que pinten el escenario)", "user_role": "El rol del usuario en la simulación", "bot_role": "El rol del personaje que va a jugar la IA", "initial_bot_message": "Primer mensaje que abre la conversación (como si fuera el bot_role)", "max_turns": 4}}

Personaliza para {rol_label}: usa vocabulario, desafíos y situaciones relevantes a ese rol."""

        try:
            response = self._client.chat.completions.create(
                model='gpt-4o-mini',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}],
            )
            response_text = response.choices[0].message.content.strip()
            
            # Intentar parsear el JSON
            import json
            scenario_data = json.loads(response_text)
            
            return scenario_data
        except Exception as exc:
            logger.error('Error generating dynamic scenario for role %s: %s', rol_it, exc)
            raise RuntimeError(f'Error al generar escenario dinámico para rol {rol_it}') from exc

    # ──────────────────────────────────────────────────────────────────
    #  Prompt de sistema
    # ──────────────────────────────────────────────────────────────────

    def generate_system_prompt(self, scenario: SoftskillsScenario | dict, rol_it_sesion: str | None = None) -> str:
        """
        Construye el prompt de sistema a partir de los datos del escenario.
        Acepta tanto escenarios de BD (SoftskillsScenario) como dinámicos (dict).
        Opcionalmente personaliza con contexto del rol IT del usuario.

        Estructura:
          1. Contexto del rol IT (si disponible)
          2. Contexto y roles del escenario
          3. Reglas de la simulación (max_turns turnos)
          4. Formato obligatorio del Informe Final
        """
        role_context = self._get_role_context(rol_it_sesion)
        role_context_section = f"\n## Contexto del rol profesional del usuario\n{role_context}\n" if role_context else ""
        
        # Extraer datos del escenario (compatible con BD y dinámicos)
        if isinstance(scenario, dict):
            context = scenario.get('context', '')
            bot_role = scenario.get('bot_role', '')
            user_role = scenario.get('user_role', '')
            max_turns = scenario.get('max_turns', 4)
            title = scenario.get('title', 'Escenario dinámico')
        else:
            context = scenario.context
            bot_role = scenario.bot_role
            user_role = scenario.user_role
            max_turns = scenario.max_turns
            title = scenario.title
        
        return f"""Eres un facilitador de roleplay de habilidades blandas en SkillsForIT.
{role_context_section}
## Contexto del escenario
{context}

## Roles
- **Tu personaje:** {bot_role}
- **El usuario es:** {user_role}

## Reglas de la simulación
1. Mantén tu personaje ({bot_role}) durante toda la simulación.
2. Responde de forma realista y desafiante, como lo haría ese personaje en una situación real.
3. La simulación tiene exactamente {max_turns} turnos del usuario.
4. Responde a cada turno exclusivamente en el rol de {bot_role}.
5. No te adelantes ni respondas por el usuario. Una réplica por vez.
6. Cuando recibas la señal de finalización, sal del personaje y genera el Informe de Feedback.

## Formato obligatorio del Informe Final (solo al recibir la señal de finalización)

### 🎯 Informe de Feedback de SkillsForIT
**Escenario evaluado:** {title}
**Tu rol:** {user_role}

#### 🟢 Aspectos Positivos
*   [Punto fuerte 1]: Lo que hiciste muy bien durante la simulación. Te felicito por esto.
*   [Punto fuerte 2]: Tu manera de manejar la situación fue rescatable. Esto muestra tu potencial.

#### 🔴 Áreas de Mejora
*   [Área 1]: Aquí hay algo en lo que podrías crecer. Te sugiero trabajar en esto.
*   [Área 2]: En este momento dejaste una oportunidad sobre la mesa. Veamos cómo podrías haberlo hecho mejor.

#### 🚀 La Respuesta Perfecta (Nivel Senior)
"[Escribe de forma textual cómo un profesional de élite habría manejado la situación más crítica]"

#### 💡 ¿Por qué esta respuesta es más efectiva?
[Explica la psicología detrás: qué señales de seniority envía, cómo reduce fricciones y qué impacto tiene en el interlocutor]

#### 📊 Puntuación de Soft Skills
**Comunicación:** [X/10] · **Asertividad:** [X/10] · **Manejo del conflicto:** [X/10] · **Profesionalismo:** [X/10]"""

    # ──────────────────────────────────────────────────────────────────
    #  Procesamiento de turno
    # ──────────────────────────────────────────────────────────────────

    def process_turn(self, session_id: str, user_message: str) -> TurnResult:
        """
        Procesa un turno del usuario en la sesión de roleplay.

        Raises:
            RoleplaySession.DoesNotExist: si la sesión no existe.
            ValueError: si la sesión ya está completada o el mensaje está vacío.
            RuntimeError: si la API de OpenAI falla.
        """
        if not user_message or not user_message.strip():
            raise ValueError('El mensaje no puede estar vacío.')

        session: RoleplaySession = (
            RoleplaySession.objects
            .select_related('scenario')
            .get(pk=session_id)
        )

        if session.status == 'completed':
            raise ValueError('La sesión ya está completada.')

        # Usar escenario dinámico si existe, sino usar el de BD
        if session.scenario_generated:
            scenario = session.scenario_generated
        else:
            scenario = session.scenario

        # Agregar mensaje del usuario al historial
        history: list = list(session.chat_history or [])
        history.append({'role': 'user', 'content': user_message.strip()})
        session.turn_count += 1

        # Determinar max_turns del escenario (BD o dinámico)
        max_turns = scenario.get('max_turns', 4) if isinstance(scenario, dict) else scenario.max_turns
        is_final = session.turn_count >= max_turns

        # Construir mensajes para la API (pasando el rol IT si existe)
        messages: list[dict] = [
            {'role': 'system', 'content': self.generate_system_prompt(scenario, session.rol_it_sesion)},
            *history,
        ]
        if is_final:
            messages.append({'role': 'system', 'content': _INFORME_TRIGGER})

        # Llamada a OpenAI
        try:
            response = self._client.chat.completions.create(
                model='gpt-4o-mini',
                max_tokens=1500 if is_final else 512,
                messages=messages,
            )
            bot_message: str = response.choices[0].message.content
        except Exception as exc:
            logger.error('OpenAI API error en roleplay session %s: %s', session_id, exc)
            raise RuntimeError('Error al conectar con la IA.') from exc

        # Persistir respuesta del bot en el historial
        history.append({'role': 'assistant', 'content': bot_message})
        session.chat_history = history

        if is_final:
            session.informe_feedback = bot_message
            session.status = 'completed'

        session.save(update_fields=[
            'chat_history', 'turn_count', 'status', 'informe_feedback', 'updated_at',
        ])

        return TurnResult(
            bot_message=bot_message,
            turn_count=session.turn_count,
            is_final=is_final,
            informe_feedback=session.informe_feedback if is_final else None,
        )
