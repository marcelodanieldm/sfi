"""
RoleplayEngineService — Lógica de IA para el módulo de Roleplay de Soft Skills.
"""

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

    def generate_system_prompt(self, scenario: SoftskillsScenario) -> str:
        """
        Construye el prompt de sistema a partir de los datos del escenario.

        Estructura:
          1. Contexto y roles
          2. Reglas de la simulación (max_turns turnos)
          3. Formato obligatorio del Informe Final
        """
        return f"""Eres un facilitador de roleplay de habilidades blandas en SkillsForIT.

## Contexto del escenario
{scenario.context}

## Roles
- **Tu personaje:** {scenario.bot_role}
- **El usuario es:** {scenario.user_role}

## Reglas de la simulación
1. Mantén tu personaje ({scenario.bot_role}) durante toda la simulación.
2. Responde de forma realista y desafiante, como lo haría ese personaje en una situación real.
3. La simulación tiene exactamente {scenario.max_turns} turnos del usuario.
4. Responde a cada turno exclusivamente en el rol de {scenario.bot_role}.
5. No te adelantes ni respondas por el usuario. Una réplica por vez.
6. Cuando recibas la señal de finalización, sal del personaje y genera el Informe de Feedback.

## Formato obligatorio del Informe Final (solo al recibir la señal de finalización)

### 🎯 Informe de Feedback de SkillsForIT
**Escenario evaluado:** {scenario.title}
**Rol del usuario:** {scenario.user_role}

#### 🟢 Aspectos Positivos
*   [Punto fuerte 1]: Qué hizo bien el usuario durante la simulación.
*   [Punto fuerte 2]: Aspectos de comunicación o manejo de la situación rescatables.

#### 🔴 Áreas de Mejora
*   [Área 1]: Comportamiento o respuesta que podría mejorar.
*   [Área 2]: Oportunidad perdida durante la simulación.

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

        scenario = session.scenario

        # Agregar mensaje del usuario al historial
        history: list = list(session.chat_history or [])
        history.append({'role': 'user', 'content': user_message.strip()})
        session.turn_count += 1

        is_final = session.turn_count >= scenario.max_turns

        # Construir mensajes para la API
        messages: list[dict] = [
            {'role': 'system', 'content': self.generate_system_prompt(scenario)},
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
