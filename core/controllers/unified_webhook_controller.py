"""
Webhook unificado — POST /api/v1/webhooks/payments

Detecta automáticamente la pasarela por los headers HTTP y aplica
la validación de firma correspondiente. Un solo endpoint para ambas pasarelas.

Seguridad:
  1. Detección de gateway: Stripe-Signature → Stripe, x-signature → MercadoPago.
     Sin header reconocible → 400 inmediato.
  2. Validación de firma antes de leer el payload:
     - Stripe: stripe.Webhook.construct_event (HMAC-SHA256 sobre raw body)
     - MP: HMAC-SHA256(id={data.id}&request-id={x-request-id}&ts={ts}, secret)
     Firma inválida → 400 inmediato, sin procesar nada.
  3. Idempotencia: antes de modificar la DB se busca el event_id en
     ProcessedPayment. Si ya existe → 200 sin modificar nada.
  4. El event_id para Stripe es event['id'] (evt_...).
     Para MP es payload['id'] (número entero del notification center).

Mapeo de estados:
  Stripe:
    checkout.session.completed               → activa apenas se completa el checkout (no espera subscription.created)
    customer.subscription.created / updated → activo si status in (active, trialing)
    customer.subscription.deleted           → cancelado
    invoice.paid                            → confirma active (renovación)
    invoice.payment_failed                  → past_due (pago fallido)
    invoice.upcoming                        → email de recordatorio de renovación (0-7 días antes)

  MercadoPago (subscription_preapproval):
    status authorized                       → active
    status paused / pending                 → inactive
    status cancelled                        → canceled

Notificaciones por email (ambas pasarelas):
  - Confirmación al pasar a status=active (alta o reactivación).
  - Cancelación al pasar a status=canceled.

Este es el ÚNICO endpoint de webhooks para MentorIA — reemplaza a los antiguos
/api/v1/webhooks/stripe/, /api/v1/webhooks/mercadopago/ y /mentoria/api/webhook/
(consolidados acá para evitar lógica duplicada e inconsistente). Los dashboards
de Stripe y MercadoPago deben apuntar únicamente a /api/v1/webhooks/payments.

Variables requeridas en settings:
  STRIPE_WEBHOOK_SECRET
  MP_WEBHOOK_SECRET
  MP_ACCESS_TOKEN
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone as dt_tz

import stripe
from django.conf import settings
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import MentorIASubscription, ProcessedPayment

logger = logging.getLogger(__name__)

# ── Status maps ──────────────────────────────────────────────────────────────
_STRIPE_ACTIVE_STATUSES = {'active', 'trialing'}
_MP_STATUS_MAP = {
    'authorized': 'active',
    'pending':    'inactive',
    'paused':     'inactive',
    'cancelled':  'canceled',
}


# ────────────────────────────────────────────────────────────────────────────
#  Idempotencia
# ────────────────────────────────────────────────────────────────────────────

def _already_processed(event_id: str) -> bool:
    return ProcessedPayment.objects.filter(event_id=event_id).exists()


def _mark_processed(event_id: str, gateway: str, event_type: str):
    try:
        ProcessedPayment.objects.create(
            event_id=event_id, gateway=gateway, event_type=event_type,
        )
    except IntegrityError:
        pass  # race condition: otro worker lo procesó primero, ignorar


# ────────────────────────────────────────────────────────────────────────────
#  Validación de firmas
# ────────────────────────────────────────────────────────────────────────────

def _parse_stripe_event(request):
    """
    Construye y valida el evento de Stripe usando el raw body y la firma.
    Devuelve el objeto evento o lanza stripe.error.SignatureVerificationError.
    """
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    secret     = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    return stripe.Webhook.construct_event(request.body, sig_header, secret)


def _validate_mp_signature(request) -> bool:
    """
    Valida la firma HMAC-SHA256 de MercadoPago (Notifications v2).
    x-signature: ts=<timestamp>,v1=<hex>
    Manifest: id={data.id}&request-id={x-request-id}&ts={ts}
    """
    secret = getattr(settings, 'MP_WEBHOOK_SECRET', '')
    if not secret:
        logger.warning('MP_WEBHOOK_SECRET no configurado')
        return False

    sig_header = request.META.get('HTTP_X_SIGNATURE', '')
    request_id = request.META.get('HTTP_X_REQUEST_ID', '')
    data_id    = request.GET.get('data.id') or request.GET.get('id', '')

    if not sig_header:
        return False

    parts = {}
    for chunk in sig_header.split(','):
        if '=' in chunk:
            k, v = chunk.split('=', 1)
            parts[k.strip()] = v.strip()

    ts = parts.get('ts', '')
    v1 = parts.get('v1', '')

    if not ts or not v1:
        return False

    manifest = f'id={data_id}&request-id={request_id}&ts={ts}'
    expected = hmac.new(
        secret.encode(), manifest.encode(), hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, v1)


# ────────────────────────────────────────────────────────────────────────────
#  Helpers de sincronización de suscripción
# ────────────────────────────────────────────────────────────────────────────

def _ts(timestamp) -> datetime | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=dt_tz.utc)


def _find_sub_by_stripe(customer_id: str, sub_id: str):
    sub = MentorIASubscription.objects.filter(stripe_subscription_id=sub_id).first()
    if not sub:
        sub = MentorIASubscription.objects.filter(stripe_customer_id=customer_id).first()
    return sub


def _billing_cycle_from_metadata(obj) -> str:
    metadata = obj.get('metadata') or {}
    billing_cycle = metadata.get('billing_cycle', 'monthly')
    return billing_cycle if billing_cycle in ('monthly', 'bimonthly') else 'monthly'


def _notify_stripe_change(sub, old_status: str, period_end):
    """Envía email de confirmación/cancelación si el status cambió de forma relevante."""
    from core.services.email_service import (
        send_subscription_confirmation_email,
        send_subscription_cancellation_email,
    )
    try:
        if sub.status == 'active' and old_status != 'active':
            send_subscription_confirmation_email(sub.user, 'stripe', period_end)
        elif sub.status == 'canceled' and old_status != 'canceled':
            send_subscription_cancellation_email(sub.user, 'stripe')
    except Exception as exc:
        logger.error('Error enviando email Stripe (sub=%s): %s', sub.stripe_subscription_id, exc)


def _upsert_stripe_sub(stripe_sub, status_override: str | None = None, user_id: str = '', billing_cycle: str = ''):
    """Crea o actualiza MentorIASubscription a partir de un stripe.Subscription."""
    from core.models import User
    sub_id      = stripe_sub.get('id', '')
    customer_id = stripe_sub.get('customer', '')
    status      = status_override or (
        'active' if stripe_sub.get('status') in _STRIPE_ACTIVE_STATUSES else
        'canceled' if stripe_sub.get('status') == 'canceled' else 'inactive'
    )
    period_end = _ts(stripe_sub.get('current_period_end'))

    defaults = {
        'payment_provider':       'stripe',
        'billing_cycle':          billing_cycle if billing_cycle in ('monthly', 'bimonthly') else _billing_cycle_from_metadata(stripe_sub),
        'stripe_subscription_id': sub_id,
        'stripe_customer_id':     customer_id,
        'status':                 status,
        'current_period_end':     period_end,
    }

    # Buscar registro existente
    sub = _find_sub_by_stripe(customer_id, sub_id)
    if sub:
        old_status = sub.status
        for k, v in defaults.items():
            setattr(sub, k, v)
        sub.save(update_fields=list(defaults.keys()) + ['updated_at'])
        _notify_stripe_change(sub, old_status, period_end)
        return

    if user_id:
        try:
            user = User.objects.get(id=user_id)
            existing = MentorIASubscription.objects.filter(user=user).first()
            old_status = existing.status if existing else ''
            sub, created = MentorIASubscription.objects.update_or_create(user=user, defaults=defaults)
            _notify_stripe_change(sub, '' if created else old_status, period_end)
            return
        except (User.DoesNotExist, ValueError):
            pass

    # Intentar vincular por email del customer
    try:
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        customer = stripe.Customer.retrieve(customer_id)
        email    = (customer.get('email') or '').lower().strip()
        if email:
            user = User.objects.filter(email=email).first()
            if user:
                existing = MentorIASubscription.objects.filter(user=user).first()
                old_status = existing.status if existing else ''
                sub, _created = MentorIASubscription.objects.update_or_create(user=user, defaults=defaults)
                _notify_stripe_change(sub, old_status, period_end)
                return
    except Exception as exc:
        logger.error('Error al resolver customer Stripe %s: %s', customer_id, exc)

    logger.warning('No se pudo vincular suscripción Stripe %s', sub_id)


def _handle_invoice_upcoming(invoice):
    """invoice.upcoming — envía recordatorio de renovación si vence en 0-7 días."""
    from core.services.email_service import send_renewal_reminder_email

    customer_id   = invoice.get('customer', '')
    period_end_ts = invoice.get('period_end') or invoice.get('lines', {}).get('data', [{}])[0].get('period', {}).get('end')

    sub = MentorIASubscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return

    period_end = sub.current_period_end or _ts(period_end_ts)
    if not period_end:
        return

    days = (period_end - datetime.now(dt_tz.utc)).days
    if 0 < days <= 7:
        try:
            send_renewal_reminder_email(sub.user, 'stripe', period_end, days)
        except Exception as exc:
            logger.error('Error enviando recordatorio de renovación Stripe: %s', exc)


def sync_mp_subscription(preapproval_id: str):
    """
    Recupera el preapproval de MP y actualiza MentorIASubscription, enviando
    email de confirmación/cancelación cuando corresponda.

    Función pública: además de ser usada por el webhook, la reutilizan
    mentor_ia_controller.mentor_ia_mp_checkout_success y mentor_ia_mp_sync
    para reconciliar "en caliente" cuando el usuario vuelve del checkout o
    pide sincronizar manualmente.
    """
    import mercadopago
    from core.models import User
    from core.services.email_service import (
        send_subscription_confirmation_email,
        send_subscription_cancellation_email,
    )

    sdk = mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))
    try:
        result = sdk.preapproval().get(preapproval_id)
        if result['status'] != 200:
            logger.error('MP preapproval GET falló: %s', result)
            return
        preapproval = result['response']
    except Exception as exc:
        logger.error('Error al obtener preapproval MP %s: %s', preapproval_id, exc)
        return

    mp_status    = preapproval.get('status', 'pending')
    local_status = _MP_STATUS_MAP.get(mp_status, 'inactive')
    payer_id     = str(preapproval.get('payer_id', ''))
    payer_email  = preapproval.get('payer_email', '')
    external_ref = preapproval.get('external_reference', '')
    user_ref, _, billing_cycle = external_ref.partition(':')
    if billing_cycle not in ('monthly', 'bimonthly', 'quarterly'):
        billing_cycle = 'monthly'

    next_payment = preapproval.get('next_payment_date')
    period_end   = None
    if next_payment:
        try:
            period_end = datetime.fromisoformat(next_payment.replace('Z', '+00:00'))
        except ValueError:
            pass

    defaults = {
        'payment_provider': 'mercadopago',
        'billing_cycle':    billing_cycle,
        'mp_preapproval_id': preapproval_id,
        'mp_payer_id':       payer_id,
        'status':            local_status,
        'current_period_end': period_end,
    }

    def _notify(sub, old_status):
        try:
            if local_status == 'active' and old_status != 'active':
                send_subscription_confirmation_email(sub.user, 'mercadopago', period_end)
            elif local_status == 'canceled' and old_status != 'canceled':
                send_subscription_cancellation_email(sub.user, 'mercadopago')
        except Exception as exc:
            logger.error('Error enviando email MP (preapproval=%s): %s', preapproval_id, exc)

    # 1. Buscar por preapproval_id (caso habitual — checkout ya guardó el id)
    sub = MentorIASubscription.objects.filter(mp_preapproval_id=preapproval_id).first()
    if sub:
        old_status = sub.status
        for field, value in defaults.items():
            setattr(sub, field, value)
        sub.save(update_fields=list(defaults.keys()) + ['updated_at'])
        logger.info('MP sub sincronizada: preapproval=%s status=%s', preapproval_id, local_status)
        _notify(sub, old_status)
        return

    # 2. Buscar por external_reference (= user_id guardado en el checkout)
    if user_ref:
        try:
            user = User.objects.get(id=user_ref)
            existing = MentorIASubscription.objects.filter(user=user).first()
            old_status = existing.status if existing else ''
            sub, created = MentorIASubscription.objects.update_or_create(user=user, defaults=defaults)
            logger.info('MP sub vinculada por external_ref: user=%s status=%s', user_ref, local_status)
            _notify(sub, '' if created else old_status)
            return
        except (User.DoesNotExist, ValueError):
            pass

    # 3. Buscar por email del pagador
    if payer_email:
        try:
            user = User.objects.get(email=payer_email.lower().strip())
            existing = MentorIASubscription.objects.filter(user=user).first()
            old_status = existing.status if existing else ''
            sub, created = MentorIASubscription.objects.update_or_create(user=user, defaults=defaults)
            logger.info('MP sub vinculada por email: %s status=%s', payer_email, local_status)
            _notify(sub, '' if created else old_status)
            return
        except User.DoesNotExist:
            pass

    logger.warning('No se pudo vincular preapproval %s a ningún usuario', preapproval_id)


# ────────────────────────────────────────────────────────────────────────────
#  Handlers por gateway
# ────────────────────────────────────────────────────────────────────────────

_STRIPE_HANDLED = {
    'checkout.session.completed',
    'customer.subscription.created',
    'customer.subscription.updated',
    'customer.subscription.deleted',
    'invoice.paid',
    'invoice.payment_failed',
    'invoice.upcoming',
}


def _handle_stripe(event):
    event_type = event['type']
    data       = event['data']['object']

    if event_type not in _STRIPE_HANDLED:
        return 'ignored'

    if event_type == 'checkout.session.completed':
        if data.get('mode') != 'subscription':
            return 'ignored'
        sub_id = data.get('subscription')
        if sub_id:
            try:
                stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
                stripe_sub = stripe.Subscription.retrieve(sub_id)
                metadata = data.get('metadata') or {}
                _upsert_stripe_sub(
                    stripe_sub,
                    user_id=metadata.get('user_id', ''),
                    billing_cycle=_billing_cycle_from_metadata(data),
                )
            except Exception as exc:
                logger.error('checkout.session.completed: error al recuperar sub %s: %s', sub_id, exc)

    elif event_type in ('customer.subscription.created', 'customer.subscription.updated'):
        _upsert_stripe_sub(data)

    elif event_type == 'customer.subscription.deleted':
        _upsert_stripe_sub(data, status_override='canceled')

    elif event_type == 'invoice.paid':
        sub_id = data.get('subscription')
        if sub_id:
            try:
                stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
                stripe_sub = stripe.Subscription.retrieve(sub_id)
                _upsert_stripe_sub(stripe_sub)
            except Exception as exc:
                logger.error('invoice.paid: error al recuperar sub %s: %s', sub_id, exc)

    elif event_type == 'invoice.payment_failed':
        sub_id = data.get('subscription')
        if sub_id:
            MentorIASubscription.objects.filter(
                stripe_subscription_id=sub_id,
            ).update(status='past_due')

    elif event_type == 'invoice.upcoming':
        _handle_invoice_upcoming(data)

    return 'ok'


def _handle_mp(payload):
    if payload.get('type') != 'subscription_preapproval':
        return 'ignored'
    preapproval_id = payload.get('data', {}).get('id', '')
    if not preapproval_id:
        return 'error'
    sync_mp_subscription(str(preapproval_id))
    return 'ok'


# ────────────────────────────────────────────────────────────────────────────
#  Endpoint unificado
# ────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def unified_webhook(request):
    """
    POST /api/v1/webhooks/payments

    Detecta la pasarela por headers:
      HTTP_STRIPE_SIGNATURE  → Stripe
      HTTP_X_SIGNATURE       → MercadoPago

    Flujo:
      1. Detectar gateway
      2. Validar firma (400 si falla)
      3. Extraer event_id
      4. Verificar idempotencia (200 si ya procesado)
      5. Procesar evento
      6. Registrar en ProcessedPayment
      7. Retornar 200
    """
    has_stripe_sig = bool(request.META.get('HTTP_STRIPE_SIGNATURE'))
    has_mp_sig     = bool(request.META.get('HTTP_X_SIGNATURE'))

    # ── 1. Detectar gateway ───────────────────────────────────────────────
    if has_stripe_sig:
        gateway = 'stripe'
    elif has_mp_sig:
        gateway = 'mercadopago'
    else:
        logger.warning('Webhook en /api/v1/webhooks/payments sin header de firma reconocible')
        return JsonResponse({'error': 'Gateway not identified'}, status=400)

    # ── 2. Validar firma ──────────────────────────────────────────────────
    if gateway == 'stripe':
        try:
            event = _parse_stripe_event(request)
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            logger.warning('Stripe firma inválida: %s', exc)
            return JsonResponse({'error': 'Invalid Stripe signature'}, status=400)

        event_id   = event['id']
        event_type = event['type']

    else:  # mercadopago
        if not _validate_mp_signature(request):
            logger.warning('MercadoPago firma inválida — IP %s', request.META.get('REMOTE_ADDR'))
            return JsonResponse({'error': 'Invalid MercadoPago signature'}, status=400)

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        event_id   = str(payload.get('id', ''))
        event_type = payload.get('type', 'subscription_preapproval')

        if not event_id:
            return JsonResponse({'error': 'Missing event id'}, status=400)

    logger.info('Webhook unificado: gateway=%s type=%s id=%s', gateway, event_type, event_id)

    # ── 3. Idempotencia ───────────────────────────────────────────────────
    if _already_processed(event_id):
        logger.info('Evento ya procesado (idempotente): %s', event_id)
        return JsonResponse({'status': 'already_processed', 'event_id': event_id})

    # ── 4. Procesar ───────────────────────────────────────────────────────
    try:
        result = _handle_stripe(event) if gateway == 'stripe' else _handle_mp(payload)
    except Exception as exc:
        logger.exception('Error procesando evento %s/%s: %s', gateway, event_id, exc)
        # No registramos en ProcessedPayment — Stripe/MP reintentará
        return JsonResponse({'error': 'Processing error'}, status=500)

    # ── 5. Registrar idempotencia ─────────────────────────────────────────
    if result != 'ignored':
        _mark_processed(event_id, gateway, event_type)

    return JsonResponse({'status': result, 'event_id': event_id})
