"""
MentorIA — Coach de Soft Skills IT disponible 24/7.

Rutas:
  GET  /mentoria/                    → landing (o redirect a chat si es suscriptor)
  POST /mentoria/checkout/           → crea sesión de checkout en Stripe
  GET  /mentoria/checkout/success/   → retorno desde Stripe, activa suscripción
  GET  /mentoria/checkout/cancel/    → cancelación del checkout
  GET  /mentoria/chat/               → interfaz de chat (requiere suscripción)
  POST /mentoria/api/session/        → crea sesión de evaluación + mensaje inicial de la IA
  POST /mentoria/api/message/<id>/   → envía mensaje del usuario, devuelve respuesta de la IA
  POST /mentoria/api/webhook/        → webhook de Stripe para gestionar suscripciones
"""

import json
import logging

import openai
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required as _login_required
login_required = _login_required(redirect_field_name='')
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

_NUCLEO = """Eres mentorIA, un Coach de Soft Skills experto en la industria tecnológica global. Tu objetivo es evaluar al usuario mediante escenarios situacionales reales del mundo del software.

Reglas del flujo conversacional:
1. Lanza UNA sola pregunta situacional compleja y realista de acuerdo al módulo elegido por el usuario.
2. Espera la respuesta del usuario humano. No te adelantes ni respondas por él.
3. Cuando el usuario responda, analiza su estructura verbal, empatía, madurez profesional y liderazgo técnico.

Estructura obligatoria del informe final (Output en formato Markdown):

### 🎯 Informe de Evaluación de Soft Skills
**Área evaluada:** [Nombre del Módulo]

#### 🟢 Aspectos Positivos
*   [Punto fuerte 1]: Explicación de qué hizo bien el usuario en su respuesta.
*   [Punto fuerte 2]: Aspectos de liderazgo o claridad técnica rescatables.

#### 🚀 La Respuesta Perfecta (Nivel Staff / Principal Dev)
"[Escribe aquí de forma textual cómo un profesional de élite habría redactado exactamente esa respuesta, usando vocabulario de alto impacto corporativo y asertividad]"

#### 💡 ¿Por qué esta opción es mejor?
[Explica la psicología detrás de la respuesta perfecta: qué hilos mueve en los mánagers, cómo reduce fricciones en el equipo y cómo demuestra seniority técnico sin sonar agresivo]."""

_SYSTEM_PROMPTS = {
    'entrevistas': _NUCLEO + """

Módulo: **Entrevistas de Trabajo**
Lanza una behavioral question realista de entrevista tech (ej: "Contame de un conflicto técnico que hayas tenido con un compañero y cómo lo resolviste"). Evaluá usando el framework STAR.""",

    'resolucion': _NUCLEO + """

Módulo: **Resolución de Problemas**
Lanza un escenario técnico con un problema complejo y real (sistema caído en producción, bug crítico sin reproducir, decisión de arquitectura bajo presión de tiempo, etc.). Pedí al usuario su proceso de análisis y plan de acción.

Ejemplo de escenario: "Tu aplicación en producción empieza a dar errores 500 esporádicos a las 3am. El sistema de alertas te despertó. ¿Cuáles son tus primeros 3 pasos?".""",

    'trabajo_equipo': _NUCLEO + """

Módulo: **Trabajo en Equipo**
Lanza una situación de equipo desafiante y realista (conflicto con PM sobre alcance, dev que bloquea al equipo, sprint comprometido, feedback difícil de dar, etc.).

Ejemplo de escenario: "Un dev de tu equipo lleva 3 días bloqueado en una tarea y no pide ayuda. Esto está retrasando el sprint. ¿Qué hacés?".""",

    'comunicacion': _NUCLEO + """

Módulo: **Comunicación Asertiva**
Lanza una situación donde la comunicación es el factor clave. Pedí que el usuario escriba textualmente lo que diría — no una descripción, el texto real.

Ejemplo de escenario: "Tu Tech Lead te pide estimar una tarea en 2 días, pero sabés que toma 6. ¿Cómo le respondés?".""",

    'proactividad': _NUCLEO + """

Módulo: **Proactividad**
Lanza una situación donde hay una oportunidad clara de proactividad que el usuario podría estar ignorando (proceso ineficiente que todos toleran, bug conocido no escalado, mejora técnica sin proponer, documentación inexistente, etc.).

Ejemplo de escenario: "Notaste que el proceso de deploy manual lleva 40 minutos y ocurre 3 veces por semana. Nadie se queja, pero todos pierden tiempo. ¿Qué hacés con eso?".""",
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
    if user.is_superuser:
        return True
    sub = _get_subscription(user)
    return sub is not None and sub.is_active


def _openai_client():
    return openai.OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))


def _stripe_client():
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    return stripe


# ────────────────────────────────────────────────────────────────────────────
#  Landing / Paywall
# ────────────────────────────────────────────────────────────────────────────

def mentor_ia(request):
    """
    GET /mentoria/
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
    POST /mentoria/checkout/
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
            'success_url': f'{site_url}/mentoria/checkout/success/?session_id={{CHECKOUT_SESSION_ID}}',
            'cancel_url': f'{site_url}/mentoria/',
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
    GET /mentoria/checkout/success/
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


# ────────────────────────────────────────────────────────────────────────────
#  MercadoPago Checkout
# ────────────────────────────────────────────────────────────────────────────

def _mp_sdk():
    import mercadopago
    return mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))


@login_required
@require_POST
def mentor_ia_mp_checkout(request):
    """
    POST /mentoria/mp/checkout/
    Crea un Preapproval de MercadoPago para la suscripción mensual
    y redirige al usuario al init_point de pago.
    """
    access_token = getattr(settings, 'MP_ACCESS_TOKEN', '')
    if not access_token:
        logger.error('MP_ACCESS_TOKEN no configurado')
        return redirect('core:mentor_ia')

    site_url = getattr(settings, 'SITE_URL', 'https://skillsforit.online')
    amount   = float(getattr(settings, 'MP_SUBSCRIPTION_AMOUNT', '9990'))
    currency = getattr(settings, 'MP_SUBSCRIPTION_CURRENCY', 'ARS')

    sdk = _mp_sdk()

    plan_id = getattr(settings, 'MP_PREAPPROVAL_PLAN_ID', '')

    if plan_id:
        # Con Plan ID (recomendado) — equivalente a STRIPE_MENTORIA_PRICE_ID
        preapproval_data = {
            'preapproval_plan_id': plan_id,
            'payer_email':         request.user.email,
            'back_url':            f'{site_url}/mentoria/mp/checkout/success/',
            'status':              'pending',
            'external_reference':  str(request.user.id),
        }
    else:
        # Sin Plan ID — precio definido directamente (fallback)
        preapproval_data = {
            'reason':      'MentorIA — Coach de Soft Skills IT',
            'payer_email': request.user.email,
            'auto_recurring': {
                'frequency':          1,
                'frequency_type':     'months',
                'transaction_amount': amount,
                'currency_id':        currency,
            },
            'back_url':           f'{site_url}/mentoria/mp/checkout/success/',
            'status':             'pending',
            'external_reference': str(request.user.id),
        }

    try:
        result = sdk.preapproval().create(preapproval_data)
        if result['status'] not in (200, 201):
            logger.error('MP preapproval error: %s', result)
            return redirect('core:mentor_ia')

        preapproval = result['response']

        # Guardamos el preapproval_id pendiente para vincularlo en el webhook
        MentorIASubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'payment_provider': 'mercadopago',
                'mp_preapproval_id': preapproval['id'],
                'status': 'inactive',
            },
        )

        return redirect(preapproval['init_point'])

    except Exception as exc:
        logger.error('MP checkout error: %s', exc)
        return redirect('core:mentor_ia')


@login_required
def mentor_ia_mp_checkout_success(request):
    """
    GET /mentoria/mp/checkout/success/
    MercadoPago redirige aquí tras el pago. El estado real llega por webhook;
    mostramos el chat y dejamos que el webhook active la suscripción.
    """
    return redirect('core:mentor_ia_chat')


def mentor_ia_mp_checkout_cancel(request):
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
def mentor_ia_subscription(request):
    """GET /mentoria/suscripcion/ — Página de gestión de suscripción."""
    sub = _get_subscription(request.user)
    return render(request, 'core/mentor_ia/subscription.html', {
        'sub': sub,
        'precio': PRECIO_MENSUAL,
    })


@login_required
@require_POST
@csrf_exempt
def mentor_ia_mp_cancel(request):
    """POST /mentoria/mp/cancel/ — Cancela el preapproval activo de MercadoPago."""
    sub = _get_subscription(request.user)
    if not sub or sub.payment_provider != 'mercadopago' or not sub.mp_preapproval_id:
        return JsonResponse({'error': 'No tenés una suscripción de MercadoPago activa.'}, status=400)

    try:
        sdk = _mp_sdk()
        result = sdk.preapproval().update(sub.mp_preapproval_id, {'status': 'cancelled'})
        if result['status'] not in (200, 201):
            logger.error('MP cancel error: %s', result)
            return JsonResponse({'error': 'Error al cancelar en MercadoPago.'}, status=500)
        sub.status = 'canceled'
        sub.save(update_fields=['status', 'updated_at'])
        return JsonResponse({'ok': True})
    except Exception as exc:
        logger.error('MP cancel error: %s', exc)
        return JsonResponse({'error': 'Error al cancelar la suscripción.'}, status=500)


@login_required
def mentor_ia_chat(request):
    """
    GET /mentoria/chat/
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
    POST /mentoria/api/session/
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
        client = _openai_client()
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=1024,
            messages=[
                {'role': 'system',  'content': _SYSTEM_PROMPTS[tipo]},
                {'role': 'user',    'content': 'Comenzá la sesión de evaluación.'},
            ],
        )
        ai_text = response.choices[0].message.content
    except Exception as exc:
        logger.error('OpenAI API error en nueva sesión: %s', exc)
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
    POST /mentoria/api/message/<session_id>/
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
        client = _openai_client()
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=1024,
            messages=[
                {'role': 'system', 'content': _SYSTEM_PROMPTS[session.tipo]},
                *history,
            ],
        )
        ai_text = response.choices[0].message.content
    except Exception as exc:
        logger.error('OpenAI API error al enviar mensaje: %s', exc)
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
    POST /mentoria/api/webhook/
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

    if event_type == 'customer.subscription.created':
        _handle_subscription_change(data, is_new=True)
    elif event_type == 'customer.subscription.updated':
        _handle_subscription_change(data, is_new=False)
    elif event_type == 'customer.subscription.deleted':
        _handle_subscription_deleted(data)
    elif event_type == 'invoice.upcoming':
        _handle_invoice_upcoming(data)

    return JsonResponse({'status': 'ok'})


def _handle_subscription_change(subscription, is_new=False):
    from datetime import datetime
    from core.models import User
    from core.services.email_service import send_subscription_confirmation_email

    customer_id = subscription.get('customer', '')
    sub_id = subscription.get('id', '')
    status = subscription.get('status', 'inactive')

    period_end_ts = subscription.get('current_period_end')
    period_end = timezone.make_aware(
        datetime.utcfromtimestamp(period_end_ts), timezone.utc,
    ) if period_end_ts else None

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
            sub, _ = MentorIASubscription.objects.update_or_create(
                user=user,
                defaults={
                    'stripe_customer_id':     customer_id,
                    'stripe_subscription_id': sub_id,
                    'status':                 status,
                    'current_period_end':     period_end,
                },
            )
            logger.info('MentorIA subscription created via webhook: %s (%s)', sub_id, email)
            if is_new and status == 'active':
                send_subscription_confirmation_email(user, 'stripe', period_end)
        except Exception as exc:
            logger.error('No se pudo vincular suscripción por webhook: %s', exc)
        return

    if is_new and status == 'active':
        try:
            send_subscription_confirmation_email(existing.user, 'stripe', period_end)
        except Exception as exc:
            logger.error('Error enviando email de confirmación Stripe: %s', exc)


def _handle_subscription_deleted(subscription):
    from core.services.email_service import send_subscription_cancellation_email

    sub_id = subscription.get('id', '')
    try:
        sub = MentorIASubscription.objects.get(stripe_subscription_id=sub_id)
        sub.status = 'canceled'
        sub.save(update_fields=['status', 'updated_at'])
        logger.info('MentorIA subscription canceled: %s', sub_id)
        try:
            send_subscription_cancellation_email(sub.user, 'stripe')
        except Exception as exc:
            logger.error('Error enviando email de cancelación Stripe: %s', exc)
    except MentorIASubscription.DoesNotExist:
        pass


def _handle_invoice_upcoming(invoice):
    from datetime import datetime
    from core.services.email_service import send_renewal_reminder_email

    customer_id = invoice.get('customer', '')
    period_end_ts = invoice.get('period_end') or invoice.get('lines', {}).get('data', [{}])[0].get('period', {}).get('end')

    try:
        sub = MentorIASubscription.objects.get(stripe_customer_id=customer_id)
        period_end = sub.current_period_end
        if not period_end and period_end_ts:
            period_end = timezone.make_aware(datetime.utcfromtimestamp(period_end_ts), timezone.utc)
        if period_end:
            now = timezone.now()
            days = (period_end - now).days
            if 0 < days <= 7:
                send_renewal_reminder_email(sub.user, 'stripe', period_end, days)
    except MentorIASubscription.DoesNotExist:
        pass
    except Exception as exc:
        logger.error('Error procesando invoice.upcoming: %s', exc)
