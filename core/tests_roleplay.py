"""
Tests para el módulo de Softskills Roleplay.

Cobertura:
  - RoleplayServiceUnitTests  → lógica interna del servicio (sin HTTP, OpenAI mockeado)
  - RoleplayAPIIntegrationTests → endpoints de la API con base de datos real

Ejecutar:
    python manage.py test core.tests_roleplay
    python manage.py test core.tests_roleplay.RoleplayServiceUnitTests
"""

import json
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse

from core.models import RoleplaySession, SoftskillsScenario, User
from core.services.roleplay_engine import RoleplayEngineService, _INFORME_TRIGGER


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers compartidos
# ─────────────────────────────────────────────────────────────────────────────

def _openai_response(text: str) -> MagicMock:
    """Construye un mock mínimo de respuesta de OpenAI."""
    return MagicMock(choices=[MagicMock(message=MagicMock(content=text))])


_SCENARIO_DEFAULTS = {
    'category':            'communication',
    'title':               'Negociación de plazo con Tech Lead',
    'context':             'Tu Tech Lead te presiona para entregar en 2 días una tarea que tardará 6.',
    'user_role':           'Desarrollador Junior',
    'bot_role':            'Tech Lead exigente',
    'initial_bot_message': '¿Cuándo me tenés el feature listo?',
    'max_turns':           4,
}

_FAKE_INFORME = (
    '### 🎯 Informe de Feedback de SkillsForIT\n'
    '**Escenario evaluado:** Negociación de plazo con Tech Lead\n'
    '#### 🟢 Aspectos Positivos\n*   Comunicación directa.\n'
    '#### 🔴 Áreas de Mejora\n*   Faltó más asertividad.\n'
    '#### 📊 Puntuación\n**Comunicación:** 7/10 · **Asertividad:** 6/10'
)


# ─────────────────────────────────────────────────────────────────────────────
#  Unit tests — RoleplayEngineService (sin HTTP)
# ─────────────────────────────────────────────────────────────────────────────

class RoleplayServiceUnitTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='unit_user', email='unit@example.com', password='Test1234!',
        )
        self.scenario = SoftskillsScenario.objects.create(**_SCENARIO_DEFAULTS)
        self.session = RoleplaySession.objects.create(
            user=self.user,
            scenario=self.scenario,
            chat_history=[{'role': 'assistant', 'content': self.scenario.initial_bot_message}],
        )

    # ── generate_system_prompt ────────────────────────────────────────────────

    def test_system_prompt_embeds_all_scenario_fields(self):
        prompt = RoleplayEngineService().generate_system_prompt(self.scenario)

        self.assertIn(self.scenario.context, prompt)
        self.assertIn(self.scenario.bot_role, prompt)
        self.assertIn(self.scenario.user_role, prompt)
        self.assertIn(self.scenario.title, prompt)
        self.assertIn(str(self.scenario.max_turns), prompt)

    def test_system_prompt_contains_informe_sections(self):
        prompt = RoleplayEngineService().generate_system_prompt(self.scenario)

        for section in ('Informe de Feedback', 'Aspectos Positivos', 'Áreas de Mejora', 'Puntuación'):
            self.assertIn(section, prompt, f'Sección "{section}" ausente del prompt')

    # ── process_turn: validaciones ────────────────────────────────────────────

    def test_process_turn_raises_on_empty_message(self):
        with self.assertRaises(ValueError):
            RoleplayEngineService().process_turn(str(self.session.id), '   ')

    def test_process_turn_raises_on_blank_message(self):
        with self.assertRaises(ValueError):
            RoleplayEngineService().process_turn(str(self.session.id), '')

    def test_process_turn_raises_on_completed_session(self):
        self.session.status = 'completed'
        self.session.save()

        with self.assertRaises(ValueError):
            RoleplayEngineService().process_turn(str(self.session.id), 'Mensaje tardío')

    # ── process_turn: incremento de turno ────────────────────────────────────

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_process_turn_increments_turn_count(self, mock_openai_class):
        mock_openai_class.return_value.chat.completions.create.return_value = (
            _openai_response('Respuesta del bot')
        )
        service = RoleplayEngineService()
        result = service.process_turn(str(self.session.id), 'Mi primer mensaje')

        self.session.refresh_from_db()
        self.assertEqual(self.session.turn_count, 1)
        self.assertEqual(result['turn_count'], 1)

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_process_turn_accumulates_chat_history(self, mock_openai_class):
        mock_openai_class.return_value.chat.completions.create.return_value = (
            _openai_response('Réplica del personaje')
        )
        initial_len = len(self.session.chat_history)

        RoleplayEngineService().process_turn(str(self.session.id), 'Mensaje de usuario')

        self.session.refresh_from_db()
        # Debe agregar el mensaje del usuario + la respuesta del bot
        self.assertEqual(len(self.session.chat_history), initial_len + 2)
        self.assertEqual(self.session.chat_history[-2]['role'], 'user')
        self.assertEqual(self.session.chat_history[-2]['content'], 'Mensaje de usuario')
        self.assertEqual(self.session.chat_history[-1]['role'], 'assistant')
        self.assertEqual(self.session.chat_history[-1]['content'], 'Réplica del personaje')

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_non_final_turn_returns_is_final_false(self, mock_openai_class):
        mock_openai_class.return_value.chat.completions.create.return_value = (
            _openai_response('Respuesta')
        )
        result = RoleplayEngineService().process_turn(str(self.session.id), 'Mensaje')

        self.assertFalse(result['is_final'])
        self.assertIsNone(result['informe_feedback'])

    # ── process_turn: turno final ─────────────────────────────────────────────

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_final_turn_injects_informe_trigger(self, mock_openai_class):
        """El _INFORME_TRIGGER debe estar en los mensajes enviados a la API en el último turno."""
        mock_create = mock_openai_class.return_value.chat.completions.create
        mock_create.return_value = _openai_response(_FAKE_INFORME)

        self.session.turn_count = self.scenario.max_turns - 1
        self.session.save()

        RoleplayEngineService().process_turn(str(self.session.id), 'Mi última respuesta')

        messages_sent = mock_create.call_args.kwargs['messages']
        trigger_found = any(m['content'] == _INFORME_TRIGGER for m in messages_sent)
        self.assertTrue(trigger_found, 'El _INFORME_TRIGGER debe inyectarse en el turno final')

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_final_turn_marks_session_completed(self, mock_openai_class):
        mock_openai_class.return_value.chat.completions.create.return_value = (
            _openai_response(_FAKE_INFORME)
        )
        self.session.turn_count = self.scenario.max_turns - 1
        self.session.save()

        result = RoleplayEngineService().process_turn(str(self.session.id), 'Mensaje final')

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'completed')
        self.assertEqual(self.session.informe_feedback, _FAKE_INFORME)
        self.assertTrue(result['is_final'])
        self.assertEqual(result['informe_feedback'], _FAKE_INFORME)
        self.assertEqual(result['bot_message'], _FAKE_INFORME)

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_non_final_turn_does_not_complete_session(self, mock_openai_class):
        mock_openai_class.return_value.chat.completions.create.return_value = (
            _openai_response('Respuesta intermedia')
        )
        # Sesión en el antepenúltimo turno (no el penúltimo)
        self.session.turn_count = self.scenario.max_turns - 2
        self.session.save()

        RoleplayEngineService().process_turn(str(self.session.id), 'Mensaje')

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'in_progress')
        self.assertIsNone(self.session.informe_feedback)


# ─────────────────────────────────────────────────────────────────────────────
#  Integration tests — API endpoints
# ─────────────────────────────────────────────────────────────────────────────

class RoleplayAPIIntegrationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='api_user', email='api@example.com', password='Test1234!',
        )
        self.scenario = SoftskillsScenario.objects.create(**_SCENARIO_DEFAULTS)
        self.client = Client()
        self.client.force_login(self.user)

    def _create_session(self, turn_count: int = 0) -> RoleplaySession:
        return RoleplaySession.objects.create(
            user=self.user,
            scenario=self.scenario,
            turn_count=turn_count,
            chat_history=[{'role': 'assistant', 'content': self.scenario.initial_bot_message}],
        )

    def _post_json(self, url: str, payload: dict):
        return self.client.post(url, data=json.dumps(payload), content_type='application/json')

    # ── GET /api/v1/roleplay/scenarios/ ──────────────────────────────────────

    def test_list_scenarios_returns_all(self):
        url = reverse('core:roleplay_list_scenarios')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('scenarios', data)
        self.assertEqual(len(data['scenarios']), 1)
        scenario = data['scenarios'][0]
        self.assertEqual(scenario['title'], self.scenario.title)
        self.assertEqual(scenario['category'], 'communication')
        self.assertIn('user_role', scenario)
        self.assertIn('bot_role', scenario)
        self.assertIn('max_turns', scenario)

    def test_list_scenarios_filters_by_category(self):
        SoftskillsScenario.objects.create(
            **{**_SCENARIO_DEFAULTS, 'category': 'leadership', 'title': 'Liderazgo en crisis'},
        )
        url = reverse('core:roleplay_list_scenarios') + '?category=communication'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['scenarios']), 1)
        self.assertEqual(data['scenarios'][0]['category'], 'communication')

    def test_list_scenarios_empty_when_category_has_no_entries(self):
        url = reverse('core:roleplay_list_scenarios') + '?category=innovation'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['scenarios'], [])

    def test_list_scenarios_rejects_invalid_category(self):
        url = reverse('core:roleplay_list_scenarios') + '?category=xyz'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_list_scenarios_requires_login(self):
        self.client.logout()
        url = reverse('core:roleplay_list_scenarios')
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 401, 403])

    # ── POST /api/v1/roleplay/sessions/start/ ────────────────────────────────

    def test_start_session_returns_201_with_initial_bot_message(self):
        """
        Al iniciar una sesión, la respuesta debe incluir el initial_bot_message
        del escenario y el session_id de la sesión recién creada.
        """
        url = reverse('core:roleplay_start_session')
        response = self._post_json(url, {'scenario_id': self.scenario.id})

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('session_id', data)
        self.assertIn('initial_bot_message', data)
        self.assertIn('scenario', data)
        self.assertEqual(data['initial_bot_message'], self.scenario.initial_bot_message)

    def test_start_session_persists_correct_initial_state(self):
        url = reverse('core:roleplay_start_session')
        response = self._post_json(url, {'scenario_id': self.scenario.id})

        session = RoleplaySession.objects.get(pk=response.json()['session_id'])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.scenario, self.scenario)
        self.assertEqual(session.turn_count, 0)
        self.assertEqual(session.status, 'in_progress')
        # El historial inicial tiene solo el mensaje del bot
        self.assertEqual(len(session.chat_history), 1)
        self.assertEqual(session.chat_history[0]['role'], 'assistant')
        self.assertEqual(session.chat_history[0]['content'], self.scenario.initial_bot_message)

    def test_start_session_rejects_missing_scenario_id(self):
        url = reverse('core:roleplay_start_session')
        response = self._post_json(url, {})
        self.assertEqual(response.status_code, 400)

    def test_start_session_rejects_non_integer_scenario_id(self):
        url = reverse('core:roleplay_start_session')
        response = self._post_json(url, {'scenario_id': 'no-soy-entero'})
        self.assertEqual(response.status_code, 400)

    def test_start_session_rejects_nonexistent_scenario(self):
        url = reverse('core:roleplay_start_session')
        response = self._post_json(url, {'scenario_id': 99999})
        self.assertEqual(response.status_code, 404)

    def test_start_session_rejects_invalid_json(self):
        url = reverse('core:roleplay_start_session')
        response = self.client.post(url, data='not-json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    # ── POST /api/v1/roleplay/sessions/<id>/message/ ─────────────────────────

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_send_message_increments_turn_count(self, mock_openai_class):
        """El contador de turnos debe incrementarse con cada mensaje del usuario."""
        mock_openai_class.return_value.chat.completions.create.return_value = (
            _openai_response('Respuesta del personaje')
        )
        session = self._create_session()
        url = reverse('core:roleplay_send_message', kwargs={'session_id': session.id})

        response = self._post_json(url, {'userMessage': 'Necesito más tiempo para esta tarea.'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['turn_count'], 1)
        self.assertFalse(data['is_final'])
        self.assertIsNone(data['informe_feedback'])
        self.assertEqual(data['bot_message'], 'Respuesta del personaje')

        session.refresh_from_db()
        self.assertEqual(session.turn_count, 1)

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_send_message_accumulates_turns(self, mock_openai_class):
        mock_openai_class.return_value.chat.completions.create.return_value = (
            _openai_response('OK')
        )
        session = self._create_session()
        url = reverse('core:roleplay_send_message', kwargs={'session_id': session.id})

        for expected_turn in range(1, 4):
            response = self._post_json(url, {'userMessage': f'Mensaje {expected_turn}'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['turn_count'], expected_turn)

        session.refresh_from_db()
        self.assertEqual(session.turn_count, 3)

    def test_send_message_rejects_empty_user_message(self):
        session = self._create_session()
        url = reverse('core:roleplay_send_message', kwargs={'session_id': session.id})

        response = self._post_json(url, {'userMessage': '   '})
        self.assertEqual(response.status_code, 400)

    def test_send_message_rejects_missing_user_message(self):
        session = self._create_session()
        url = reverse('core:roleplay_send_message', kwargs={'session_id': session.id})

        response = self._post_json(url, {})
        self.assertEqual(response.status_code, 400)

    def test_send_message_rejects_completed_session(self):
        session = self._create_session()
        session.status = 'completed'
        session.save()
        url = reverse('core:roleplay_send_message', kwargs={'session_id': session.id})

        response = self._post_json(url, {'userMessage': 'Intento continuar una sesión cerrada'})
        self.assertEqual(response.status_code, 409)

    def test_send_message_rejects_another_users_session(self):
        other_user = User.objects.create_user(
            username='otro', email='otro@example.com', password='Otro1234!',
        )
        other_session = RoleplaySession.objects.create(
            user=other_user, scenario=self.scenario, chat_history=[],
        )
        url = reverse('core:roleplay_send_message', kwargs={'session_id': other_session.id})

        response = self._post_json(url, {'userMessage': 'Intento acceder a sesión ajena'})
        self.assertEqual(response.status_code, 404)

    # ── Flujo completo: 4 turnos → sesión completada ──────────────────────────

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_full_flow_four_turns_completes_session_with_informe(self, mock_openai_class):
        """
        Flujo completo mockeado:
          - Turnos 1-3: respuestas del personaje, sesión en 'in_progress'.
          - Turno 4:    la IA genera el informe, sesión pasa a 'completed',
                        'informe_feedback' contiene el texto del informe.
        """
        mock_create = mock_openai_class.return_value.chat.completions.create
        mock_create.side_effect = [
            _openai_response('El deadline es el deadline.'),
            _openai_response('No me interesan las excusas.'),
            _openai_response('Tenés 3 días, no más.'),
            _openai_response(_FAKE_INFORME),
        ]

        session = self._create_session()
        url = reverse('core:roleplay_send_message', kwargs={'session_id': session.id})

        user_messages = [
            'Necesito más tiempo para esta tarea.',
            'La estimación no contemplaba los bugs del legacy.',
            'Puedo entregarlo en 5 días con calidad garantizada.',
            'Entiendo. Haré lo posible para cumplir.',
        ]

        for turn_number, msg in enumerate(user_messages, start=1):
            response = self._post_json(url, {'userMessage': msg})

            self.assertEqual(response.status_code, 200, f'Fallo en turno {turn_number}')
            data = response.json()
            self.assertEqual(data['turn_count'], turn_number, f'turn_count incorrecto en turno {turn_number}')

            if turn_number < 4:
                self.assertFalse(data['is_final'], f'Turno {turn_number} no debe ser final')
                self.assertIsNone(data['informe_feedback'])
            else:
                # Turno 4: turno final
                self.assertTrue(data['is_final'], 'El turno 4 debe ser el final')
                self.assertEqual(data['bot_message'], _FAKE_INFORME)
                self.assertEqual(data['informe_feedback'], _FAKE_INFORME)

        # Verificar estado final en base de datos
        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
        self.assertEqual(session.turn_count, 4)
        self.assertIsNotNone(session.informe_feedback)
        self.assertEqual(session.informe_feedback, _FAKE_INFORME)

        # Historial: 1 mensaje inicial + 4 pares (user + assistant) = 9
        self.assertEqual(len(session.chat_history), 9)

        # La API de OpenAI se llamó exactamente 4 veces
        self.assertEqual(mock_create.call_count, 4)

    @patch('core.services.roleplay_engine.openai.OpenAI')
    def test_full_flow_openai_uses_max_tokens_1500_on_final_turn(self, mock_openai_class):
        """El turno final debe usar max_tokens=1500 para dar espacio al informe."""
        mock_create = mock_openai_class.return_value.chat.completions.create
        mock_create.return_value = _openai_response(_FAKE_INFORME)

        session = self._create_session(turn_count=self.scenario.max_turns - 1)
        url = reverse('core:roleplay_send_message', kwargs={'session_id': session.id})

        self._post_json(url, {'userMessage': 'Mensaje final'})

        call_kwargs = mock_create.call_args.kwargs
        self.assertEqual(call_kwargs['max_tokens'], 1500)
