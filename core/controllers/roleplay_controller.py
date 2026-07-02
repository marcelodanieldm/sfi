"""
Roleplay Controller — Páginas y API para el módulo de Roleplay de Soft Skills.

Páginas:
  GET  /roleplay/                                    → selector de escenarios
  GET  /roleplay/chat/<uuid>/                        → interfaz de chat

API:
  GET  /api/v1/roleplay/scenarios/                   → catálogo filtrado por category
  POST /api/v1/roleplay/sessions/start/              → crea sesión y devuelve contexto inicial
  POST /api/v1/roleplay/sessions/<uuid>/message/     → procesa un turno del usuario
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from core.models import RoleplaySession, SoftskillsScenario
from core.services.roleplay_engine import RoleplayEngineService

logger = logging.getLogger(__name__)

_VALID_CATEGORIES = {
    'communication', 'leadership', 'negotiation',
    'critical-thinking', 'innovation', 'career',
}


# ──────────────────────────────────────────────────────────────────────────────
#  Páginas HTML (montan las apps Vue)
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def roleplay_selector(request):
    """
    GET /roleplay/?category=<slug>
    Renderiza el selector de escenarios. El parámetro category es opcional;
    Vue lo usa para filtrar el catálogo via API en el cliente.
    """
    category = request.GET.get('category', '').strip()
    if category and category not in _VALID_CATEGORIES:
        category = ''
    return render(request, 'core/roleplay/scenario_selector.html', {
        'category': category,
    })


@login_required
def roleplay_chat_page(request, session_id):
    """
    GET /roleplay/chat/<uuid:session_id>/
    Renderiza la interfaz de chat para una sesión existente.
    Verifica que la sesión pertenezca al usuario actual.
    """
    session = get_object_or_404(RoleplaySession.objects.select_related('scenario'),
                                pk=session_id, user=request.user)
    scenario = session.scenario

    # Primer mensaje del historial o el campo estático del escenario como fallback
    if session.chat_history:
        initial_bot_message = session.chat_history[0].get('content', scenario.initial_bot_message)
    else:
        initial_bot_message = scenario.initial_bot_message

    # Diccionario que Vue leerá via json_script
    scenario_json = {
        'id':        scenario.id,
        'category':  scenario.category,
        'title':     scenario.title,
        'context':   scenario.context,
        'user_role': scenario.user_role,
        'bot_role':  scenario.bot_role,
        'max_turns': scenario.max_turns,
    }

    return render(request, 'core/roleplay/roleplay_chat.html', {
        'session':              session,
        'scenario_json':        scenario_json,
        'initial_bot_message':  initial_bot_message,
    })


# ──────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/roleplay/sessions/<uuid>/
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def roleplay_get_session(request, session_id):
    """
    Devuelve el estado completo de una sesión para hidratación del store
    cuando el usuario navega directamente a /soft-skills/roleplay/:sessionId
    (p. ej. al refrescar la página).
    """
    session = get_object_or_404(RoleplaySession.objects.select_related('scenario'),
                                pk=session_id, user=request.user)
    scenario = session.scenario
    return JsonResponse({
        'session_id':       str(session.id),
        'status':           session.status,
        'turn_count':       session.turn_count,
        'chat_history':     session.chat_history,
        'informe_feedback': session.informe_feedback,
        'scenario': {
            'id':        scenario.id,
            'category':  scenario.category,
            'title':     scenario.title,
            'context':   scenario.context,
            'user_role': scenario.user_role,
            'bot_role':  scenario.bot_role,
            'max_turns': scenario.max_turns,
        },
    })


# ──────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/roleplay/scenarios/
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def roleplay_list_scenarios(request):
    """
    Devuelve el catálogo de escenarios, filtrado opcionalmente por category.

    Query params:
      category (str, opcional): una de communication | leadership | negotiation |
                                critical-thinking | innovation | career
    """
    category = request.GET.get('category', '').strip()

    qs = SoftskillsScenario.objects.order_by('?')
    if category:
        if category not in _VALID_CATEGORIES:
            return JsonResponse(
                {'error': f"Categoría inválida. Opciones: {', '.join(sorted(_VALID_CATEGORIES))}"},
                status=400,
            )
        qs = qs.filter(category=category)

    scenarios = [
        {
            'id':             s.id,
            'category':       s.category,
            'category_label': s.get_category_display(),
            'title':          s.title,
            'context':        s.context,
            'user_role':      s.user_role,
            'bot_role':       s.bot_role,
            'max_turns':      s.max_turns,
        }
        for s in qs
    ]

    return JsonResponse({'scenarios': scenarios})


# ──────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/roleplay/sessions/start/
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@csrf_exempt
@require_POST
def roleplay_start_session(request):
    """
    Crea una nueva sesión de roleplay y devuelve el contexto inicial.

    Body JSON:
      scenario_id (int, requerido): ID del escenario a simular.

    Respuesta 201:
      session_id (str): UUID de la sesión creada.
      scenario   (obj): Datos del escenario (título, contexto, roles, max_turns).
      initial_bot_message (str): Primer mensaje del bot para pintar en el chat.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    scenario_id = data.get('scenario_id')
    if not scenario_id:
        return JsonResponse({'error': 'scenario_id es requerido'}, status=400)
    if not isinstance(scenario_id, int):
        return JsonResponse({'error': 'scenario_id debe ser un entero'}, status=400)

    try:
        scenario = SoftskillsScenario.objects.get(pk=scenario_id)
    except SoftskillsScenario.DoesNotExist:
        return JsonResponse({'error': 'Escenario no encontrado'}, status=404)

    initial_message = scenario.initial_bot_message
    session = RoleplaySession.objects.create(
        user=request.user,
        scenario=scenario,
        turn_count=0,
        chat_history=[{'role': 'assistant', 'content': initial_message}],
    )

    return JsonResponse(
        {
            'session_id': str(session.id),
            'scenario': {
                'id':       scenario.id,
                'title':    scenario.title,
                'context':  scenario.context,
                'user_role': scenario.user_role,
                'bot_role':  scenario.bot_role,
                'max_turns': scenario.max_turns,
            },
            'initial_bot_message': initial_message,
        },
        status=201,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/roleplay/sessions/<uuid:session_id>/message/
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@csrf_exempt
@require_POST
def roleplay_send_message(request, session_id):
    """
    Procesa el turno del usuario y devuelve la réplica del bot.

    Body JSON:
      userMessage (str, requerido): Mensaje del usuario en la simulación.

    Respuesta 200:
      bot_message      (str):       Réplica del bot (personaje o informe final).
      turn_count       (int):       Turno actual después de procesar.
      is_final         (bool):      True si la sesión acaba de completarse.
      informe_feedback (str|null):  Informe completo, presente solo en el turno final.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    user_message = data.get('userMessage', '').strip()
    if not user_message:
        return JsonResponse({'error': 'userMessage es requerido y no puede estar vacío'}, status=400)

    # Verificar que la sesión existe y pertenece al usuario
    try:
        RoleplaySession.objects.get(pk=session_id, user=request.user)
    except RoleplaySession.DoesNotExist:
        return JsonResponse({'error': 'Sesión no encontrada'}, status=404)

    try:
        result = RoleplayEngineService().process_turn(str(session_id), user_message)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=409)
    except RuntimeError:
        return JsonResponse({'error': 'Error al procesar el turno. Intentá de nuevo.'}, status=502)

    return JsonResponse({
        'bot_message':      result['bot_message'],
        'turn_count':       result['turn_count'],
        'is_final':         result['is_final'],
        'informe_feedback': result['informe_feedback'],
    })
