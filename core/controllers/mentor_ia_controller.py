"""
MentorIA — Coach de Soft Skills IT disponible 24/7.

Rutas:
  GET  /mentor-ia/                    → landing (o redirect a chat si es suscriptor)
  POST /mentor-ia/checkout/           → crea sesión de checkout en Stripe
  GET  /mentor-ia/checkout/success/   → retorno desde Stripe, activa suscripción
  GET  /mentor-ia/checkout/cancel/    → cancelación del checkout
  GET  /mentor-ia/chat/               → interfaz de chat (requiere suscripción)
  POST /mentor-ia/api/session/        → crea sesión de evaluación + mensaje inicial de la IA
  POST /mentor-ia/api/message/<id>/   → envía mensaje del usuario, devuelve respuesta de la IA
  POST /mentor-ia/api/webhook/        → webhook de Stripe para gestionar suscripciones
"""

import json
import logging

import anthropic
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import MentorIAMessage, MentorIASession, MentorIASubscription

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────
#  Prompts del sistema por tipo de evaluación
# ────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPTS = {
    'entrevistas': """Eres MentorIA, un coach experto en soft skills IT especializado en preparación para entrevistas de trabajo en tecnología. Evaluás las habilidades comunicativas y profesionales del candidato a través de simulaciones de entrevista reales.

FLUJO DE LA SESIÓN:
1. Presentate brevemente y explicá el ejercicio (2-3 líneas)
2. Presentá una behavioral question típica de entrevistas tech (ej: "Contame de un conflicto técnico que hayas tenido con un compañero")
3. Esperá la respuesta del usuario
4. Evaluá usando el framework STAR (Situación, Tarea, Acción, Resultado): señalá fortalezas y áreas de mejora con puntaje 1-10
5. Mostrá cómo mejorar la respuesta con un ejemplo concreto
6. Preguntá si quieren practicar con otra pregunta

Sé directo, constructivo y específico. Nada de generalismos vacíos. Usá español rioplatense informal pero profesional.""",

    'resolucion': """Eres MentorIA, coach de pensamiento crítico y resolución de problemas para profesionales IT. Evaluás cómo el usuario analiza, descompone y resuelve problemas complejos en entornos técnicos.

FLUJO DE LA SESIÓN:
1. Presentate y describí el ejercicio brevemente
2. Presentá un escenario técnico real con un problema complejo (sistema caído en producción, bug crítico sin reproducir, prioridades en conflicto, etc.)
3. Pedí al usuario que describa su proceso de análisis y plan de acción
4. Evaluá: velocidad de diagnóstico, estructura del análisis, consideración de impactos, comunicación hacia el equipo
5. Dá feedback concreto con lo que haría un senior en ese rol
6. Ofrece explorar variantes del problema o un nuevo escenario

Sé riguroso. Los problemas deben ser realistas y desafiantes, no triviales.""",

    'trabajo_equipo': """Eres MentorIA, coach especializado en colaboración ágil y dinámica de equipos técnicos. Evaluás habilidades de trabajo en equipo, comunicación y resolución de conflictos en contextos IT.

FLUJO DE LA SESIÓN:
1. Presentate y explicá el ejercicio
2. Describí una situación de equipo desafiante y realista (conflicto con PM sobre alcance, dev que bloquea al equipo, sprint comprometido por deuda técnica, feedback difícil de dar, etc.)
3. Preguntá cómo el usuario manejaría exactamente esa situación
4. Evaluá: comunicación, empatía, asertividad, orientación a soluciones, impacto en el equipo
5. Mostrá con un ejemplo cómo respondería alguien con alta madurez en trabajo en equipo
6. Explorá otro escenario si el usuario quiere

Sé empático pero exigente. Los equipos técnicos tienen dinámicas únicas que hay que entender.""",

    'comunicacion': """Eres MentorIA, coach de comunicación asertiva para desarrolladores, QAs y líderes técnicos. Tu objetivo es que el usuario se comunique de forma clara, directa y empática en contextos profesionales IT.

FLUJO DE LA SESIÓN:
1. Presentate y describí el ejercicio
2. Presentá una situación concreta donde la comunicación es el factor clave (presentar resultados técnicos a stakeholders no técnicos, dar feedback en un code review, negociar plazos imposibles, explicar deuda técnica, dar malas noticias)
3. Pedí que el usuario escriba exactamente lo que diría en esa situación (texto real, no descripción)
4. Evaluá: claridad, asertividad, empatía, ausencia de tecnicismos innecesarios, impacto esperado
5. Reescribí un ejemplo mejorado y explicá punto por punto por qué funciona mejor
6. Practicá otra situación

Exigís que escriban el texto real porque ahí está la diferencia entre saber y poder comunicar.""",

    'proactividad': """Eres MentorIA, coach de proactividad e iniciativa para profesionales IT. Evaluás la capacidad del usuario para anticipar problemas, proponer mejoras y generar impacto sin esperar instrucciones.

FLUJO DE LA SESIÓN:
1. Presentate y describí el ejercicio
2. Describí una situación donde hay una oportunidad clara de proactividad que el usuario podría estar ignorando (proceso ineficiente que todos toleran, bug conocido no escalado, mejora técnica obvia sin proponer, documentación inexistente, etc.)
3. Preguntá qué haría el usuario en esa situación y por qué
4. Evaluá: nivel de iniciativa real vs teórico, impacto de las acciones propuestas, forma de comunicar el valor
5. Mostrá la diferencia entre un dev reactivo y uno proactivo con ejemplos concretos
6. Discutí cómo medir y hacer visible el impacto de ser proactivo (para reviews de performance, negociaciones salariales, etc.)

La proactividad sin visibilidad no existe. Eso es lo que hay que trabajar.""",
}

_TIPO_LABELS = {
    'entrevistas':    'Entrevistas de trabajo',
    'resolucion':     'Resolución de problemas',
    'trabajo_equipo': 'Trabajo en equipo',
    'comunicacion':   'Comunicación asertiva',
    'proactividad':   'Proactividad',
}

PRECIO_MENSUAL = '9.99'


# ────────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────────

def _get_subscription(user):
    try:
        return user.mentoria_subscription
    except MentorIASubscription.DoesNotExist:
        return None


def _is_subscriber(user):
    sub = _get_subscription(user)
    return sub is not None and sub.is_active


def _anthropic_client():
    return anthropic.Anthropic(api_key=getattr(settings, 'ANTHROPIC_API_KEY', ''))


def _stripe_client():
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    return stripe


# ────────────────────────────────────────────────────────────────────────────
#  Landing / Paywall
# ────────────────────────────────────────────────────────────────────────────

def mentor_ia(request):
    """
    GET /mentor-ia/
    Si el usuario está autenticado y tiene suscripción activa → redirect al chat.
    Si no → landing con planes y CTA de checkout.
    """
    if request.user.is_authenticated and _is_subscriber(request.user):
        return redirect('core:mentor_ia_chat')

    return render(request, 'core/mentor_ia/landing.html', {
        'precio_mensual': PRECIO_MENSUAL,
        'is_authenticated': request.user.is_authenticated,
    })


# ────────────────────────────────────────────────────────────────────────────
#  Stripe Checkout
# ────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def mentor_ia_checkout(request):
    """
    POST /mentor-ia/checkout/
    Crea una sesión de checkout en Stripe para la suscripción mensual.
    """
    _stripe_client()
    price_id = getattr(settings, 'STRIPE_MENTORIA_PRICE_ID', '')
    if not price_id:
        logger.error('STRIPE_MENTORIA_PRICE_ID no configurado')
        return redirect('core:mentor_ia')

    sub = _get_subscription(request.user)
    customer_id = sub.stripe_customer_id if sub else None

    site_url = getattr(settings, 'SITE_URL', 'https://skillsforit.online')

    try:
        params = {
            'mode': 'subscription',
            'line_items': [{'price': price_id, 'quantity': 1}],
            'success_url': f'{site_url}/mentor-ia/checkout/success/?session_id={{CHECKOUT_SESSION_ID}}',
            'cancel_url': f'{site_url}/mentor-ia/',
            'metadata': {'user_id': str(request.user.id)},
        }
        if customer_id:
            params['customer'] = customer_id
        else:
            params['customer_email'] = request.user.email

        session = stripe.checkout.Session.create(**params)
        return redirect(session.url)

    except stripe.error.StripeError as exc:
        logger.error('Stripe checkout error: %s', exc)
        return redirect('core:mentor_ia')


@login_required
def mentor_ia_checkout_success(request):
    """
    GET /mentor-ia/checkout/success/
    Retorno desde Stripe tras checkout exitoso.
    Activa la suscripción localmente si el webhook aún no llegó.
    """
    _stripe_client()
    session_id = request.GET.get('session_id', '')
    if session_id:
        try:
            checkout_session = stripe.checkout.Session.retrieve(
                session_id, expand=['subscription', 'customer']
            )
            _activate_subscription(
                user=request.user,
                stripe_customer_id=checkout_session.customer.id if checkout_session.customer else '',
                stripe_subscription=checkout_session.subscription,
            )
        except Exception as exc:
            logger.error('Error activating subscription on success redirect: %s', exc)

    return redirect('core:mentor_ia_chat')


def mentor_ia_checkout_cancel(request):
    return redirect('core:mentor_ia')


def _activate_subscription(user, stripe_customer_id, stripe_subscription):
    """Crea o actualiza MentorIASubscription desde un objeto stripe.Subscription."""
    if not stripe_subscription:
        return

    if isinstance(stripe_subscription, str):
        stripe_subscription = stripe.Subscription.retrieve(stripe_subscription)

    period_end = None
    if stripe_subscription.current_period_end:
        from datetime import datetime
        period_end = timezone.make_aware(
            datetime.utcfromtimestamp(stripe_subscription.current_period_end),
            timezone.utc,
        )

    MentorIASubscription.objects.update_or_create(
        user=user,
        defaults={
            'stripe_customer_id':     stripe_customer_id,
            'stripe_subscription_id': stripe_subscription.id,
            'status':                 stripe_subscription.status,
            'current_period_end':     period_end,
        },
    )


# ────────────────────────────────────────────────────────────────────────────
#  Chat
# ────────────────────────────────────────────────────────────────────────────

@login_required
def mentor_ia_chat(request):
    """
    GET /mentor-ia/chat/
    Interfaz de chat. Requiere suscripción activa.
    """
    if not _is_subscriber(request.user):
        return redirect('core:mentor_ia')

    return render(request, 'core/mentor_ia/chat.html', {
        'tipos': list(_TIPO_LABELS.items()),
    })


# ────────────────────────────────────────────────────────────────────────────
#  API: nueva sesión de evaluación
# ────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
@csrf_exempt
def mentor_ia_api_new_session(request):
    """
    POST /mentor-ia/api/session/
    Body JSON: {"tipo": "entrevistas"}
    Crea una sesión, pide a la IA el mensaje de apertura y lo devuelve.
    """
    if not _is_subscriber(request.user):
        return JsonResponse({'error': 'Suscripción requerida'}, status=403)

    try:
        data = json.loads(request.body)
        tipo = data.get('tipo', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if tipo not in _SYSTEM_PROMPTS:
        return JsonResponse({'error': 'Tipo de evaluación inválido'}, status=400)

    session = MentorIASession.objects.create(user=request.user, tipo=tipo)

    try:
        client = _anthropic_client()
        response = client.messages.create(
            model='claude-haiku-4-5',
            max_tokens=1024,
            system=_SYSTEM_PROMPTS[tipo],
            messages=[{'role': 'user', 'content': 'Comenzá la sesión de evaluación.'}],
        )
        ai_text = response.content[0].text
    except Exception as exc:
        logger.error('Anthropic API error en nueva sesión: %s', exc)
        session.delete()
        return JsonResponse({'error': 'Error al conectar con la IA'}, status=502)

    MentorIAMessage.objects.create(session=session, rol='user', contenido='Comenzá la sesión de evaluación.')
    MentorIAMessage.objects.create(session=session, rol='assistant', contenido=ai_text)

    return JsonResponse({
        'session_id': str(session.id),
        'tipo_label': _TIPO_LABELS[tipo],
        'message':    ai_text,
    })


# ────────────────────────────────────────────────────────────────────────────
#  API: enviar mensaje
# ────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
@csrf_exempt
def mentor_ia_api_send_message(request, session_id):
    """
    POST /mentor-ia/api/message/<session_id>/
    Body JSON: {"message": "Mi respuesta..."}
    Guarda el mensaje del usuario, consulta la IA con el historial completo
    y devuelve la respuesta.
    El input del chat se bloquea client-side hasta recibir esta respuesta.
    """
    if not _is_subscriber(request.user):
        return JsonResponse({'error': 'Suscripción requerida'}, status=403)

    session = get_object_or_404(MentorIASession, id=session_id, user=request.user)

    try:
        data = json.loads(request.body)
        user_text = data.get('message', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if not user_text:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    MentorIAMessage.objects.create(session=session, rol='user', contenido=user_text)

    history = [
        {'role': msg.rol, 'content': msg.contenido}
        for msg in session.messages.all()
    ]

    try:
        client = _anthropic_client()
        response = client.messages.create(
            model='claude-haiku-4-5',
            max_tokens=1024,
            system=_SYSTEM_PROMPTS[session.tipo],
            messages=history,
        )
        ai_text = response.content[0].text
    except Exception as exc:
        logger.error('Anthropic API error al enviar mensaje: %s', exc)
        return JsonResponse({'error': 'Error al conectar con la IA'}, status=502)

    MentorIAMessage.objects.create(session=session, rol='assistant', contenido=ai_text)

    return JsonResponse({'message': ai_text})


# ────────────────────────────────────────────────────────────────────────────
#  Webhook de Stripe — gestión del ciclo de vida de la suscripción
# ────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def webhook_stripe_mentoria(request):
    """
    POST /mentor-ia/api/webhook/
    Maneja eventos de Stripe para mantener el estado de suscripción sincronizado.
    """
    _stripe_client()
    webhook_secret = getattr(settings, 'STRIPE_MENTORIA_WEBHOOK_SECRET', '')
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        logger.warning('Stripe MentorIA webhook: firma inválida — %s', exc)
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    event_type = event['type']
    data = event['data']['object']

    if event_type in ('customer.subscription.created', 'customer.subscription.updated'):
        _handle_subscription_change(data)
    elif event_type == 'customer.subscription.deleted':
        _handle_subscription_deleted(data)

    return JsonResponse({'status': 'ok'})


def _handle_subscription_change(subscription):
    customer_id = subscription.get('customer', '')
    sub_id = subscription.get('id', '')
    status = subscription.get('status', 'inactive')

    from datetime import datetime
    period_end_ts = subscription.get('current_period_end')
    period_end = timezone.make_aware(
        datetime.utcfromtimestamp(period_end_ts), timezone.utc,
    ) if period_end_ts else None

    from core.models import User
    try:
        existing = MentorIASubscription.objects.get(stripe_subscription_id=sub_id)
        existing.status = status
        existing.current_period_end = period_end
        existing.save(update_fields=['status', 'current_period_end', 'updated_at'])
        logger.info('MentorIA subscription updated: %s → %s', sub_id, status)
    except MentorIASubscription.DoesNotExist:
        # El evento llegó antes del redirect de success — intentamos vincular por customer
        try:
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get('email', '')
            user = User.objects.get(email=email)
            MentorIASubscription.objects.update_or_create(
                user=user,
                defaults={
                    'stripe_customer_id':     customer_id,
                    'stripe_subscription_id': sub_id,
                    'status':                 status,
                    'current_period_end':     period_end,
                },
            )
            logger.info('MentorIA subscription created via webhook: %s (%s)', sub_id, email)
        except Exception as exc:
            logger.error('No se pudo vincular suscripción por webhook: %s', exc)


def _handle_subscription_deleted(subscription):
    sub_id = subscription.get('id', '')
    try:
        sub = MentorIASubscription.objects.get(stripe_subscription_id=sub_id)
        sub.status = 'canceled'
        sub.save(update_fields=['status', 'updated_at'])
        logger.info('MentorIA subscription canceled: %s', sub_id)
    except MentorIASubscription.DoesNotExist:
        pass
