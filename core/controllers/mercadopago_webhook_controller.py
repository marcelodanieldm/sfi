"""
Webhook de MercadoPago — POST /api/v1/webhooks/mercadopago/

Gestiona el ciclo de vida completo de las suscripciones (Preapproval) de mentorIA.

Eventos manejados (tipo 'subscription_preapproval'):
  authorized  → activa la suscripción (is_active = True)
  pending     → pendiente de pago (sin cambios de acceso)
  paused      → suscripción pausada (revoca acceso)
  cancelled   → suscripción cancelada (revoca acceso)

Validación de firma (MercadoPago Notifications v2):
  Header x-signature: ts=<timestamp>,v1=<hmac>
  Manifest firmado:   id={data.id}&request-id={x-request-id}&ts={ts}
  Algoritmo:          HMAC-SHA256 con MP_WEBHOOK_SECRET

Configuración requerida en settings:
  MP_ACCESS_TOKEN       → token de acceso de MercadoPago
  MP_WEBHOOK_SECRET     → secreto del webhook (dashboard MP → Tus integraciones)
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone as dt_tz

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import MentorIASubscription

logger = logging.getLogger(__name__)

# Mapa de status de MP → status interno
_STATUS_MAP = {
    'authorized': 'active',
    'pending':    'inactive',
    'paused':     'inactive',
    'cancelled':  'canceled',
}


# ────────────────────────────────────────────────────────────────────────────
#  Validación de firma
# ────────────────────────────────────────────────────────────────────────────

def _validate_mp_signature(request) -> bool:
    """
    Valida la firma HMAC-SHA256 del webhook de MercadoPago (Notifications v2).
    Devuelve True si la firma es válida, False si no.
    Si MP_WEBHOOK_SECRET no está configurado, acepta sin validar (solo en dev).
    """
    secret = getattr(settings, 'MP_WEBHOOK_SECRET', '')
    if not secret:
        logger.warning('MP_WEBHOOK_SECRET no configurado — saltando validación de firma')
        return True

    sig_header  = request.META.get('HTTP_X_SIGNATURE', '')
    request_id  = request.META.get('HTTP_X_REQUEST_ID', '')
    data_id     = request.GET.get('data.id') or request.GET.get('id', '')

    if not sig_header:
        return False

    # Parsear ts y v1 del header: "ts=1234567890,v1=abc123def..."
    parts = {}
    for chunk in sig_header.split(','):
        if '=' in chunk:
            k, v = chunk.split('=', 1)
            parts[k.strip()] = v.strip()

    ts = parts.get('ts', '')
    v1 = parts.get('v1', '')

    if not ts or not v1:
        return False

    manifest  = f'id={data_id}&request-id={request_id}&ts={ts}'
    expected  = hmac.new(
        secret.encode('utf-8'),
        manifest.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, v1)


# ────────────────────────────────────────────────────────────────────────────
#  Sincronización de suscripción
# ────────────────────────────────────────────────────────────────────────────

def _sync_mp_subscription(preapproval_id: str):
    """
    Recupera el Preapproval de la API de MP y actualiza MentorIASubscription.
    Busca el registro local por mp_preapproval_id o external_reference (user_id).
    """
    import mercadopago
    sdk = mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))

    try:
        result = sdk.preapproval().get(preapproval_id)
        if result['status'] != 200:
            logger.error('MP preapproval GET falló: %s', result)
            return
        preapproval = result['response']
    except Exception as exc:
        logger.error('Error al consultar preapproval %s: %s', preapproval_id, exc)
        return

    mp_status    = preapproval.get('status', 'pending')
    local_status = _STATUS_MAP.get(mp_status, 'inactive')
    payer_id     = str(preapproval.get('payer_id', ''))
    payer_email  = preapproval.get('payer_email', '')
    external_ref = preapproval.get('external_reference', '')

    # Calcular next_payment_date como period_end aproximado
    next_payment = preapproval.get('next_payment_date')
    period_end   = None
    if next_payment:
        try:
            period_end = datetime.fromisoformat(next_payment.replace('Z', '+00:00'))
        except ValueError:
            pass

    from core.services.email_service import (
        send_subscription_confirmation_email,
        send_subscription_cancellation_email,
    )

    defaults = {
        'payment_provider': 'mercadopago',
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
    from core.models import User
    if external_ref:
        try:
            user = User.objects.get(id=external_ref)
            sub, created = MentorIASubscription.objects.update_or_create(
                user=user, defaults=defaults,
            )
            logger.info('MP sub vinculada por external_ref: user=%s status=%s', external_ref, local_status)
            _notify(sub, '' if created else local_status)
            return
        except User.DoesNotExist:
            pass

    # 3. Buscar por email del pagador
    if payer_email:
        try:
            user = User.objects.get(email=payer_email.lower().strip())
            sub, created = MentorIASubscription.objects.update_or_create(
                user=user, defaults=defaults,
            )
            logger.info('MP sub vinculada por email: %s status=%s', payer_email, local_status)
            _notify(sub, '' if created else local_status)
            return
        except User.DoesNotExist:
            pass

    logger.warning('No se pudo vincular preapproval %s a ningún usuario', preapproval_id)


# ────────────────────────────────────────────────────────────────────────────
#  Endpoint principal
# ────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """
    POST /api/v1/webhooks/mercadopago/

    MercadoPago envía notificaciones de tipo 'subscription_preapproval'.
    Validamos la firma, obtenemos el preapproval_id y sincronizamos el estado.
    Devuelve 200 siempre tras validación para evitar reintentos innecesarios.
    """
    if not _validate_mp_signature(request):
        logger.warning(
            'MP webhook: firma inválida — IP %s',
            request.META.get('REMOTE_ADDR'),
        )
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    notification_type = payload.get('type', '')
    action            = payload.get('action', '')
    data_id           = payload.get('data', {}).get('id', '')

    logger.info('MP webhook: type=%s action=%s id=%s', notification_type, action, data_id)

    if notification_type != 'subscription_preapproval':
        return JsonResponse({'status': 'ignored', 'type': notification_type})

    if not data_id:
        logger.warning('MP webhook subscription_preapproval sin data.id')
        return JsonResponse({'error': 'Missing data.id'}, status=400)

    try:
        _sync_mp_subscription(data_id)
    except Exception as exc:
        logger.exception('Error procesando webhook MP %s: %s', data_id, exc)

    return JsonResponse({'status': 'ok', 'preapproval_id': data_id})
