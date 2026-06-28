"""
Webhook de Stripe — POST /api/v1/webhooks/stripe/

Gestiona el ciclo de vida completo de las suscripciones de mentorIA.

Eventos manejados:
  checkout.session.completed    → activa la suscripción al finalizar el checkout
  customer.subscription.created → crea el registro local de suscripción
  customer.subscription.updated → sincroniza status y período de facturación
  customer.subscription.deleted → marca la suscripción como cancelada
  invoice.paid                  → confirma renovación y mantiene status=active
  invoice.payment_failed        → marca la suscripción como past_due

Configuración requerida en settings:
  STRIPE_SECRET_KEY
  STRIPE_WEBHOOK_SECRET       ← secreto del webhook configurado en el dashboard
  SITE_URL                    ← para resolver usuarios por customer email

El endpoint es CSRF-exempt. La autenticidad se valida con la firma HMAC
de Stripe (Stripe-Signature header). Cualquier firma inválida devuelve 400.
"""

import logging
from datetime import datetime, timezone as dt_tz

import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import MentorIASubscription

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────────

def _stripe():
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    return stripe


def _ts_to_aware(timestamp):
    """Convierte un Unix timestamp de Stripe a datetime aware (UTC)."""
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=dt_tz.utc)


def _sync_subscription(stripe_sub):
    """
    Crea o actualiza MentorIASubscription a partir de un objeto stripe.Subscription.
    Busca al usuario por stripe_subscription_id primero; si no existe, busca
    por stripe_customer_id; si tampoco, por el email del customer en Stripe.
    Devuelve la instancia actualizada o None si no puede vincularla.
    """
    sub_id      = stripe_sub.get('id', '')
    customer_id = stripe_sub.get('customer', '')
    status      = stripe_sub.get('status', 'inactive')
    period_end  = _ts_to_aware(stripe_sub.get('current_period_end'))

    defaults = {
        'stripe_customer_id':     customer_id,
        'stripe_subscription_id': sub_id,
        'status':                 status,
        'current_period_end':     period_end,
    }

    # 1. Buscar por subscription_id (caso más frecuente — suscripción ya existe)
    existing = MentorIASubscription.objects.filter(stripe_subscription_id=sub_id).first()
    if existing:
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save(update_fields=list(defaults.keys()) + ['updated_at'])
        logger.info('MentorIA sub sincronizada: id=%s status=%s', sub_id, status)
        return existing

    # 2. Buscar por customer_id (suscripción recién creada sin pasar por checkout)
    existing = MentorIASubscription.objects.filter(stripe_customer_id=customer_id).first()
    if existing:
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save(update_fields=list(defaults.keys()) + ['updated_at'])
        logger.info('MentorIA sub vinculada por customer: customer=%s status=%s', customer_id, status)
        return existing

    # 3. Buscar por email del customer en Stripe (primera suscripción del usuario)
    from core.models import User
    try:
        _stripe()
        customer = stripe.Customer.retrieve(customer_id)
        email = (customer.get('email') or '').lower().strip()
        if email:
            user = User.objects.filter(email=email).first()
            if user:
                sub, _ = MentorIASubscription.objects.update_or_create(
                    user=user, defaults=defaults,
                )
                logger.info('MentorIA sub creada via email: %s status=%s', email, status)
                return sub
    except Exception as exc:
        logger.error('Error al resolver customer en Stripe: %s', exc)

    logger.warning('No se pudo vincular suscripción Stripe %s a ningún usuario', sub_id)
    return None


# ────────────────────────────────────────────────────────────────────────────
#  Handlers por evento
# ────────────────────────────────────────────────────────────────────────────

def _on_checkout_completed(session):
    """
    checkout.session.completed
    El usuario completó el pago. Recuperamos la suscripción expandida y
    sincronizamos el estado local.
    """
    _stripe()
    mode = session.get('mode')
    if mode != 'subscription':
        return  # ignorar checkouts de pago único

    sub_id = session.get('subscription')
    if not sub_id:
        logger.warning('checkout.session.completed sin subscription_id')
        return

    try:
        stripe_sub = stripe.Subscription.retrieve(sub_id)
        _sync_subscription(stripe_sub)
    except Exception as exc:
        logger.error('Error al recuperar suscripción %s: %s', sub_id, exc)


def _on_subscription_event(stripe_sub):
    """
    customer.subscription.created / updated / deleted
    Sincroniza el estado directamente desde el objeto de suscripción del evento.
    """
    _sync_subscription(stripe_sub)


def _on_invoice_paid(invoice):
    """
    invoice.paid
    El pago del período fue exitoso. Nos aseguramos de que status=active
    y actualizamos el período aunque el evento subscription.updated llegue
    antes o después.
    """
    sub_id = invoice.get('subscription')
    if not sub_id:
        return

    sub = MentorIASubscription.objects.filter(stripe_subscription_id=sub_id).first()
    if not sub:
        logger.debug('invoice.paid: suscripción %s no encontrada localmente', sub_id)
        return

    period_end = _ts_to_aware(invoice.get('lines', {}).get('data', [{}])[0].get('period', {}).get('end'))
    sub.status = 'active'
    fields = ['status', 'updated_at']
    if period_end:
        sub.current_period_end = period_end
        fields.append('current_period_end')
    sub.save(update_fields=fields)
    logger.info('MentorIA sub renovada por invoice.paid: %s', sub_id)


def _on_invoice_payment_failed(invoice):
    """
    invoice.payment_failed
    El cobro falló. Marcamos past_due para que el paywall bloquee el acceso.
    Stripe reintentará según la configuración de dunning del dashboard.
    """
    sub_id = invoice.get('subscription')
    if not sub_id:
        return

    updated = MentorIASubscription.objects.filter(
        stripe_subscription_id=sub_id,
    ).update(status='past_due')

    if updated:
        logger.info('MentorIA sub marcada past_due por pago fallido: %s', sub_id)
    else:
        logger.warning('invoice.payment_failed: suscripción %s no encontrada', sub_id)


# ────────────────────────────────────────────────────────────────────────────
#  Endpoint principal
# ────────────────────────────────────────────────────────────────────────────

_HANDLED_EVENTS = {
    'checkout.session.completed',
    'customer.subscription.created',
    'customer.subscription.updated',
    'customer.subscription.deleted',
    'invoice.paid',
    'invoice.payment_failed',
}


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    POST /api/v1/webhooks/stripe/

    Valida la firma HMAC de Stripe y despacha al handler correspondiente.
    Devuelve 200 para todos los eventos procesados o ignorados.
    Devuelve 400 solo ante firma inválida o payload malformado.
    """
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    payload    = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    _stripe()

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        logger.warning('Stripe webhook: payload inválido')
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        logger.warning('Stripe webhook: firma inválida (posible replay o secret incorrecto)')
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    event_type = event['type']
    data       = event['data']['object']

    logger.info('Stripe webhook recibido: %s (id=%s)', event_type, event.get('id'))

    if event_type not in _HANDLED_EVENTS:
        return JsonResponse({'status': 'ignored', 'event': event_type})

    try:
        if event_type == 'checkout.session.completed':
            _on_checkout_completed(data)

        elif event_type in (
            'customer.subscription.created',
            'customer.subscription.updated',
            'customer.subscription.deleted',
        ):
            _on_subscription_event(data)

        elif event_type == 'invoice.paid':
            _on_invoice_paid(data)

        elif event_type == 'invoice.payment_failed':
            _on_invoice_payment_failed(data)

    except Exception as exc:
        # Logueamos pero devolvemos 200 para evitar reintentos infinitos de Stripe.
        # Los reintentos son apropiados solo ante errores transitorios (red, DB caída);
        # para errores lógicos repetibles causarían spam.
        logger.exception('Error procesando evento %s: %s', event_type, exc)

    return JsonResponse({'status': 'ok', 'event': event_type})
