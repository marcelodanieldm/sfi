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

from django.contrib.auth.decorators import login_required as _login_required
login_required = _login_required(redirect_field_name='')
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from core.models import MentorIASubscription, RoleplaySession, SoftskillsScenario


def _is_subscriber(user):
    if user.is_superuser:
        return True
    try:
        return user.mentoria_subscription.is_active
    except MentorIASubscription.DoesNotExist:
        return False
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
    Renderiza el selector de escenarios. Requiere suscripción activa.
    """
    if not _is_subscriber(request.user):
        return redirect('core:mentor_ia_subscription')
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
    Renderiza la interfaz de chat. Requiere suscripción activa.
    """
    if not _is_subscriber(request.user):
        return redirect('core:mentor_ia_subscription')
    session = get_object_or_404(RoleplaySession.objects.select_related('scenario'),
                                pk=session_id, user=request.user)
    
    # Manejar escenarios estáticos (FK a scenario) o dinámicamente generados (scenario=None)
    if session.scenario:
        scenario = session.scenario
        scenario_json = {
            'id':        scenario.id,
            'category':  scenario.category,
            'title':     scenario.title,
            'context':   scenario.context,
            'user_role': scenario.user_role,
            'bot_role':  scenario.bot_role,
            'max_turns': scenario.max_turns,
        }
        # Primer mensaje del historial o el campo estático del escenario como fallback
        if session.chat_history:
            initial_bot_message = session.chat_history[0].get('content', scenario.initial_bot_message)
        else:
            initial_bot_message = scenario.initial_bot_message
    else:
        # Escenario generado dinámicamente
        scenario_generated = session.scenario_generated or {}
        scenario_json = {
            'title':     scenario_generated.get('title', 'Escenario dinámico'),
            'context':   scenario_generated.get('context', ''),
            'user_role': scenario_generated.get('user_role', ''),
            'bot_role':  scenario_generated.get('bot_role', ''),
            'max_turns': scenario_generated.get('max_turns', 4),
        }
        # Usar el primer mensaje del historial (que se creó en sessions/start/)
        if session.chat_history:
            initial_bot_message = session.chat_history[0].get('content', 'Hola, ¿cómo estás?')
        else:
            initial_bot_message = scenario_generated.get('initial_bot_message', 'Hola, ¿cómo estás?')

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
        'rol_it_sesion':    session.rol_it_sesion,
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
    Crea una nueva sesión de roleplay con escenario DINÁMICAMENTE generado.

    Body JSON:
      rol_it_sesion (str, requerido): Rol IT del usuario para generar escenario personalizado.

    Respuesta 201:
      session_id (str): UUID de la sesión creada.
      scenario   (obj): Escenario generado dinámicamente (título, contexto, roles, max_turns).
      initial_bot_message (str): Primer mensaje del bot para pintar en el chat.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    # Rol IT es ahora requerido para generar el escenario
    rol_it_sesion = data.get('rol_it_sesion') or request.user.rol_it_preferido
    
    if not rol_it_sesion:
        return JsonResponse({'error': 'rol_it_sesion es requerido'}, status=400)
    
    # Validar que el rol IT sea válido
    valid_roles = dict(request.user.ROLES_IT)
    if rol_it_sesion not in valid_roles:
        return JsonResponse({'error': f'Rol IT inválido: {rol_it_sesion}'}, status=400)

    # Generar escenario dinámicamente con OpenAI
    engine = RoleplayEngineService()
    try:
        scenario_generated = engine.generate_dynamic_scenario(rol_it_sesion)
    except RuntimeError as e:
        logger.error('Error generating dynamic scenario: %s', e)
        return JsonResponse({'error': str(e)}, status=500)

    # Crear sesión con escenario generado
    initial_message = scenario_generated.get('initial_bot_message', 'Hola, ¿cómo estás?')
    
    session = RoleplaySession.objects.create(
        user=request.user,
        scenario=None,  # No hay FK a escenario predefinido
        scenario_generated=scenario_generated,
        rol_it_sesion=rol_it_sesion,
        turn_count=0,
        chat_history=[{'role': 'assistant', 'content': initial_message}],
    )

    return JsonResponse(
        {
            'session_id': str(session.id),
            'scenario': {
                'title':     scenario_generated.get('title', 'Escenario dinámico'),
                'context':   scenario_generated.get('context', ''),
                'user_role': scenario_generated.get('user_role', ''),
                'bot_role':  scenario_generated.get('bot_role', ''),
                'max_turns': scenario_generated.get('max_turns', 4),
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


# ──────────────────────────────────────────────────────────────────────────────
#  GET /api/v1/roleplay/roles/
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def roleplay_get_available_roles(request):
    """
    Devuelve los roles IT disponibles para que el usuario pueda seleccionar.
    
    Respuesta 200:
      roles (list): Lista de tuplas [valor, nombre] de los roles IT.
      user_role (str|null): Rol IT preferido actual del usuario (si tiene).
    """
    from core.models import User
    
    roles = [{'value': value, 'label': label} for value, label in User.ROLES_IT]
    
    return JsonResponse({
        'roles': roles,
        'user_role': request.user.rol_it_preferido,
    })


# ──────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/roleplay/profile/update-role/
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@csrf_exempt
@require_POST
def roleplay_update_user_role(request):
    """
    Actualiza el rol IT preferido del usuario.
    
    Body JSON:
      rol_it_preferido (str, requerido): Uno de los valores válidos de User.ROLES_IT
    
    Respuesta 200:
      rol_it_preferido (str): Rol actualizado.
    """
    from core.models import User
    
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    rol_preferido = data.get('rol_it_preferido', '').strip()
    
    if not rol_preferido:
        return JsonResponse({'error': 'rol_it_preferido es requerido'}, status=400)
    
    # Validar que sea un rol válido
    valid_roles = dict(User.ROLES_IT)
    if rol_preferido not in valid_roles:
        return JsonResponse({
            'error': f'Rol inválido. Opciones válidas: {", ".join(valid_roles.keys())}'
        }, status=400)
    
    # Actualizar el rol del usuario
    request.user.rol_it_preferido = rol_preferido
    request.user.save(update_fields=['rol_it_preferido'])
    
    return JsonResponse({
        'rol_it_preferido': rol_preferido,
        'message': 'Rol actualizado exitosamente'
    })


# ──────────────────────────────────────────────────────────────────────────────
#  POST /api/v1/roleplay/sessions/<uuid:session_id>/regenerate/
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@csrf_exempt
@require_POST
def roleplay_regenerate_scenario(request, session_id):
    """
    Regenera un nuevo escenario para la sesión si aún no ha comenzado el chat.
    Máximo 3 regeneraciones por sesión.
    
    Respuesta 200:
      scenario (obj): Nuevo escenario generado.
      initial_bot_message (str): Primer mensaje del bot con el nuevo escenario.
      regenerate_count (int): Contador de regeneraciones usadas.
    
    Respuesta 400:
      error (str): Motivo del error (session started, max regenerations, etc).
    """
    try:
        session = RoleplaySession.objects.get(pk=session_id, user=request.user)
    except RoleplaySession.DoesNotExist:
        return JsonResponse({'error': 'Sesión no encontrada'}, status=404)
    
    # Validar que no haya comenzado el chat (solo el mensaje inicial del bot)
    if len(session.chat_history or []) > 1:
        return JsonResponse({
            'error': 'No se puede regenerar un escenario si ya han intercambiado mensajes'
        }, status=400)
    
    # Validar que no haya excedido el máximo de regeneraciones
    if session.regenerate_count >= 3:
        return JsonResponse({
            'error': 'Se alcanzó el máximo de regeneraciones (3)'
        }, status=400)
    
    # Generar nuevo escenario
    engine = RoleplayEngineService()
    try:
        scenario_generated = engine.generate_dynamic_scenario(session.rol_it_sesion)
    except RuntimeError as e:
        logger.error('Error regenerating scenario: %s', e)
        return JsonResponse({'error': str(e)}, status=500)
    
    # Actualizar sesión con nuevo escenario
    initial_message = scenario_generated.get('initial_bot_message', 'Hola, ¿cómo estás?')
    session.scenario_generated = scenario_generated
    session.regenerate_count += 1
    session.chat_history = [{'role': 'assistant', 'content': initial_message}]
    session.save(update_fields=['scenario_generated', 'regenerate_count', 'chat_history', 'updated_at'])
    
    return JsonResponse({
        'scenario': {
            'title':     scenario_generated.get('title', 'Escenario dinámico'),
            'context':   scenario_generated.get('context', ''),
            'user_role': scenario_generated.get('user_role', ''),
            'bot_role':  scenario_generated.get('bot_role', ''),
            'max_turns': scenario_generated.get('max_turns', 4),
        },
        'initial_bot_message': initial_message,
        'regenerate_count': session.regenerate_count,
        'can_regenerate': session.regenerate_count < 3,
    }, status=200)
