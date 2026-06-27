"""
Webhook de Hotmart — POST /api/webhooks/hotmart/

Seguridad:
  Hotmart envía el token de verificación configurado en el dashboard como
  header  →  X-Hotmart-Webhook-Token
  o como query param  →  ?hottok=<token>
  Ambas vías son chequeadas contra settings.HOTMART_WEBHOOK_TOKEN.

Eventos manejados:
  PURCHASE_APPROVED  → crea o actualiza EbookOrder(status='approved') con
                       todos los datos del comprador para retención.

Eventos ignorados (devuelven 200 para evitar reintentos de Hotmart):
  PURCHASE_CANCELLED, PURCHASE_REFUNDED, PURCHASE_CHARGEBACK, etc.
  Se loguean pero no modifican la base de datos.
"""

import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import EbookOrder
from core.services.email_service import send_welcome_ebook_email

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
#  Validación del token
# ────────────────────────────────────────────────────────────────────────────

def _validate_token(request) -> bool:
    expected = getattr(settings, 'HOTMART_WEBHOOK_TOKEN', '')
    if not expected:
        logger.error('HOTMART_WEBHOOK_TOKEN no está configurado en settings')
        return False
    incoming = (
        request.headers.get('X-Hotmart-Webhook-Token')
        or request.GET.get('hottok', '')
    )
    return incoming == expected


# ────────────────────────────────────────────────────────────────────────────
#  Endpoint principal
# ────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def webhook_hotmart(request):
    """
    POST /api/webhooks/hotmart/

    Punto de entrada de todos los eventos de Hotmart.
    Devuelve siempre 200 una vez superada la validación del token para
    eventos no manejados; Hotmart reintenta ante cualquier 4xx/5xx.
    """
    if not _validate_token(request):
        logger.warning(
            'Hotmart webhook: token inválido — IP %s',
            request.META.get('REMOTE_ADDR'),
        )
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.error('Hotmart webhook: body no es JSON válido — %s', exc)
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = payload.get('event', '')
    logger.info('Hotmart webhook recibido: event=%s', event)

    if event == 'PURCHASE_APPROVED':
        return _handle_purchase_approved(payload)

    # Logueamos eventos no gestionados y respondemos 200 para evitar reintentos.
    logger.info('Hotmart webhook: evento "%s" ignorado', event)
    return JsonResponse({'status': 'ignored', 'event': event})


# ────────────────────────────────────────────────────────────────────────────
#  Handler: PURCHASE_APPROVED
# ────────────────────────────────────────────────────────────────────────────

def _handle_purchase_approved(payload: dict) -> JsonResponse:
    data     = payload.get('data', {})
    purchase = data.get('purchase', {})
    buyer    = data.get('buyer', {})
    product  = data.get('product', {})
    address  = buyer.get('address', {})
    price    = purchase.get('price', {})

    transaction = purchase.get('transaction', '').strip()
    if not transaction:
        logger.error('Hotmart PURCHASE_APPROVED: falta purchase.transaction')
        return JsonResponse({'error': 'Missing transaction'}, status=400)

    buyer_email = buyer.get('email', '').lower().strip()
    if not buyer_email:
        logger.error(
            'Hotmart PURCHASE_APPROVED: falta buyer.email (transaction=%s)',
            transaction,
        )
        return JsonResponse({'error': 'Missing buyer email'}, status=400)

    order, created = EbookOrder.objects.update_or_create(
        hotmart_transaction=transaction,
        defaults={
            'status':              'approved',
            'hotmart_product_id':  str(product.get('id', '')),
            'hotmart_offer_code':  purchase.get('offer', {}).get('code', ''),
            'buyer_email':         buyer_email,
            'buyer_name':          buyer.get('name', ''),
            'buyer_first_name':    buyer.get('first_name', ''),
            'buyer_last_name':     buyer.get('last_name', ''),
            'buyer_phone':         buyer.get('checkout_phone') or buyer.get('phone', ''),
            'buyer_document':      buyer.get('document', ''),
            'buyer_country':       address.get('country', ''),
            'buyer_country_iso':   address.get('country_iso', ''),
            'purchase_price':      price.get('value'),
            'purchase_currency':   price.get('currency_value', ''),
            'hotmart_payload':     payload,
            'approved_at':         timezone.now(),
        },
    )

    logger.info(
        'Hotmart PURCHASE_APPROVED: orden %s (transaction=%s, buyer=%s)',
        'creada' if created else 'actualizada',
        transaction,
        buyer_email,
    )

    # Enviamos el email de bienvenida solo en la primera confirmación.
    # Si Hotmart reintenta el webhook (orden ya existente), no reenviamos.
    if created:
        send_welcome_ebook_email(order)

    return JsonResponse({'status': 'ok', 'transaction': transaction})
