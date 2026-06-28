"""
Endpoints de pagos:
  POST /api/v1/payments/create-session  → genera URL de checkout (Stripe o MP)
  POST /api/v1/payments/portal          → genera URL del portal de autogestión Stripe

Unifica Stripe y MercadoPago en un solo endpoint que devuelve la URL de pago.
Útil para frontends estáticos o SPAs que llaman a la API y redirigen via JS.

Seguridad:
  - Requiere autenticación Django (@login_required)
  - Rate limiting en memoria: máx 5 requests/minuto por IP
  - Validación de pasarela y parámetros de entrada
  - La sesión de Stripe incluye metadata.user_id
  - El preapproval de MP incluye external_reference = user_id

Respuesta exitosa:
  {"url": "https://checkout.stripe.com/..." }   ← redirigir al usuario aquí

Respuesta de error:
  {"error": "mensaje"}, status 4xx
"""

import logging
import threading
import time
from collections import defaultdict

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
#  Rate Limiter en memoria
#  Máximo 5 requests por minuto por IP.
#  Thread-safe con lock. En producción usar Redis + django-ratelimit.
# ────────────────────────────────────────────────────────────────────────────

_RATE_LIMIT_MAX     = 5      # requests
_RATE_LIMIT_WINDOW  = 60     # segundos
_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()


def _check_rate_limit(ip: str) -> bool:
    """
    Devuelve True si la IP está dentro del límite, False si lo superó.
    Descarta timestamps fuera de la ventana antes de evaluar.
    """
    now = time.monotonic()
    with _rate_lock:
        timestamps = _rate_store[ip]
        # Descartar requests fuera de la ventana
        _rate_store[ip] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(_rate_store[ip]) >= _RATE_LIMIT_MAX:
            return False
        _rate_store[ip].append(now)
        return True


def _client_ip(request) -> str:
    """Extrae la IP real del cliente, considerando proxies."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '0.0.0.0')


# ────────────────────────────────────────────────────────────────────────────
#  Helpers de pasarela
# ────────────────────────────────────────────────────────────────────────────

def _create_stripe_session(user, site_url: str) -> str:
    """
    Crea una Stripe Checkout Session en modo subscription.
    Incluye user_id en metadata para vincularlo en el webhook.
    Devuelve la URL del checkout hosteado por Stripe.
    """
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    price_id = getattr(settings, 'STRIPE_MENTORIA_PRICE_ID', '')

    if not price_id:
        raise ValueError('STRIPE_MENTORIA_PRICE_ID no configurado')

    from core.models import MentorIASubscription
    try:
        sub = user.mentoria_subscription
        customer_id = sub.stripe_customer_id or None
    except MentorIASubscription.DoesNotExist:
        customer_id = None

    params = {
        'mode':        'subscription',
        'line_items':  [{'price': price_id, 'quantity': 1}],
        'success_url': f'{site_url}/mentor-ia/checkout/success/?session_id={{CHECKOUT_SESSION_ID}}',
        'cancel_url':  f'{site_url}/mentor-ia/',
        'metadata':    {'user_id': str(user.id)},
    }
    if customer_id:
        params['customer'] = customer_id
    else:
        params['customer_email'] = user.email

    session = stripe.checkout.Session.create(**params)
    return session.url


def _create_mp_session(user, site_url: str) -> str:
    """
    Crea un Preapproval de MercadoPago para suscripción mensual.
    Incluye external_reference = user_id para vincularlo en el webhook.
    Devuelve la URL init_point de MercadoPago.
    """
    import mercadopago
    sdk = mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))

    amount   = float(getattr(settings, 'MP_SUBSCRIPTION_AMOUNT', '9990'))
    currency = getattr(settings, 'MP_SUBSCRIPTION_CURRENCY', 'ARS')

    preapproval_data = {
        'reason':        'MentorIA — Coach de Soft Skills IT',
        'payer_email':   user.email,
        'auto_recurring': {
            'frequency':          1,
            'frequency_type':     'months',
            'transaction_amount': amount,
            'currency_id':        currency,
        },
        'back_url':           f'{site_url}/mentor-ia/mp/checkout/success/',
        'status':             'pending',
        'external_reference': str(user.id),
    }

    result = sdk.preapproval().create(preapproval_data)
    if result['status'] not in (200, 201):
        raise ValueError(f"MP preapproval error: {result.get('response', {})}")

    return result['response']['init_point']


# ────────────────────────────────────────────────────────────────────────────
#  Endpoint unificado
# ────────────────────────────────────────────────────────────────────────────

VALID_GATEWAYS = {'stripe', 'mercadopago'}


@csrf_exempt
@login_required
@require_POST
def create_payment_session(request):
    """
    POST /api/v1/payments/create-session

    Body JSON:
      { "pasarela": "stripe" | "mercadopago" }

    El userId se obtiene de la sesión autenticada de Django — nunca del body,
    para evitar que un usuario pueda crear una sesión a nombre de otro.

    Respuesta 200:
      { "url": "https://..." }

    Respuestas de error:
      400 — pasarela inválida o parámetros faltantes
      429 — rate limit superado
      500 — error en la pasarela de pago
    """
    import json

    # ── Rate limiting ──────────────────────────────────────────────────────
    ip = _client_ip(request)
    if not _check_rate_limit(ip):
        logger.warning('Rate limit superado en create-session: IP=%s user=%s', ip, request.user.id)
        return JsonResponse(
            {'error': 'Demasiadas solicitudes. Esperá un minuto e intentá de nuevo.'},
            status=429,
        )

    # ── Validar body ──────────────────────────────────────────────────────
    try:
        data    = json.loads(request.body)
        gateway = data.get('pasarela', '').strip().lower()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if gateway not in VALID_GATEWAYS:
        return JsonResponse(
            {'error': f'Pasarela inválida. Opciones: {", ".join(sorted(VALID_GATEWAYS))}'},
            status=400,
        )

    # ── Verificar que no tenga suscripción activa ya ──────────────────────
    from core.models import MentorIASubscription
    try:
        existing = request.user.mentoria_subscription
        if existing.is_active:
            return JsonResponse(
                {'error': 'Ya tenés una suscripción activa.'},
                status=400,
            )
    except MentorIASubscription.DoesNotExist:
        pass

    # ── Crear sesión de pago ──────────────────────────────────────────────
    site_url = getattr(settings, 'SITE_URL', 'https://skillsforit.online')

    try:
        if gateway == 'stripe':
            url = _create_stripe_session(request.user, site_url)
        else:
            url = _create_mp_session(request.user, site_url)

        logger.info(
            'Sesión de pago creada: gateway=%s user=%s',
            gateway, request.user.id,
        )
        return JsonResponse({'url': url})

    except stripe.error.StripeError as exc:
        logger.error('Stripe error en create-session: %s', exc)
        return JsonResponse({'error': 'Error al conectar con Stripe'}, status=500)

    except Exception as exc:
        logger.error('Error en create-session (gateway=%s): %s', gateway, exc)
        return JsonResponse({'error': 'Error al crear la sesión de pago'}, status=500)


# ────────────────────────────────────────────────────────────────────────────
#  Portal de autogestión de Stripe
# ────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@login_required
@require_POST
def create_portal_session(request):
    """
    POST /api/v1/payments/portal

    Genera una URL temporal del Stripe Customer Portal para que el usuario
    pueda gestionar su suscripción (cambiar plan, cancelar, actualizar tarjeta).

    No recibe body — el stripe_customer_id se obtiene de la sesión autenticada.

    Respuesta 200:
      { "url": "https://billing.stripe.com/session/..." }

    Respuestas de error:
      400 — el usuario no tiene suscripción Stripe registrada
      429 — rate limit superado
      503 — error al contactar Stripe
    """
    # ── Rate limiting ──────────────────────────────────────────────────────
    ip = _client_ip(request)
    if not _check_rate_limit(ip):
        return JsonResponse(
            {'error': 'Demasiadas solicitudes. Esperá un minuto e intentá de nuevo.'},
            status=429,
        )

    # ── Obtener stripe_customer_id desde DB ───────────────────────────────
    from core.models import MentorIASubscription
    try:
        sub = request.user.mentoria_subscription
    except MentorIASubscription.DoesNotExist:
        return JsonResponse({'error': 'No tenés una suscripción registrada.'}, status=400)

    customer_id = sub.stripe_customer_id
    if not customer_id:
        return JsonResponse(
            {'error': 'Tu suscripción no está vinculada a Stripe. '
                      'Si pagaste por MercadoPago, gestioná desde la app de MP.'},
            status=400,
        )

    # ── Crear sesión del portal ───────────────────────────────────────────
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    site_url = getattr(settings, 'SITE_URL', 'https://skillsforit.online')
    return_url = f'{site_url}/mentor-ia/'

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        logger.info('Portal Stripe creado: customer=%s user=%s', customer_id, request.user.id)
        return JsonResponse({'url': portal_session.url})

    except stripe.error.InvalidRequestError as exc:
        logger.error('Stripe portal InvalidRequest: %s', exc)
        return JsonResponse(
            {'error': 'No se pudo abrir el portal. Verificá que el Customer Portal '
                      'esté habilitado en tu dashboard de Stripe.'},
            status=503,
        )
    except stripe.error.StripeError as exc:
        logger.error('Stripe portal error: %s', exc)
        return JsonResponse({'error': 'Error al conectar con Stripe.'}, status=503)
