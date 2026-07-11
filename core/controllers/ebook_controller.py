import logging

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Ebook, EbookOrder

logger = logging.getLogger(__name__)


def ebook(request):
    ebooks = Ebook.objects.filter(activo=True).order_by('orden', 'titulo')
    return render(request, 'core/ebook_landing.html', {'ebooks': ebooks})


@require_POST
def ebook_mp_checkout(request, slug):
    ebook_obj = get_object_or_404(Ebook, slug=slug, activo=True)
    buyer_email = request.POST.get('email', '').lower().strip()
    if not buyer_email:
        messages.error(request, 'Ingresá tu email para continuar con MercadoPago.')
        return redirect('core:ebook')

    import mercadopago

    site_url = getattr(settings, 'SITE_URL', 'https://skillsforit.online')
    amount = float(getattr(settings, 'EBOOK_MP_AMOUNT', '19990'))
    currency = getattr(settings, 'EBOOK_MP_CURRENCY', 'ARS')
    sdk = mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))

    preference_data = {
        'items': [{
            'title': ebook_obj.titulo,
            'quantity': 1,
            'unit_price': amount,
            'currency_id': currency,
        }],
        'payer': {'email': buyer_email},
        'back_urls': {
            'success': f'{site_url}/ebook/mp/success/',
            'failure': f'{site_url}/ebook/#catalogo',
            'pending': f'{site_url}/ebook/#catalogo',
        },
        'auto_return': 'approved',
        'external_reference': f'ebook:{ebook_obj.slug}',
        'metadata': {
            'ebook_slug': ebook_obj.slug,
            'buyer_email': buyer_email,
        },
        'notification_url': f'{site_url}/webhooks/mercadopago/',
    }

    try:
        result = sdk.preference().create(preference_data)
        if result['status'] not in (200, 201):
            logger.error('MP ebook preference error: %s', result)
            messages.error(request, 'No pudimos iniciar el pago con MercadoPago. Intentá de nuevo.')
            return redirect('core:ebook')
        return redirect(result['response']['init_point'])
    except Exception as exc:
        logger.error('MP ebook checkout error: %s', exc)
        messages.error(request, 'No pudimos iniciar el pago con MercadoPago. Intentá de nuevo.')
        return redirect('core:ebook')


def ebook_mp_success(request):
    payment_id = request.GET.get('payment_id', '')
    status = request.GET.get('status', '')
    if payment_id and status == 'approved':
        try:
            _confirm_mp_ebook_payment(payment_id)
            messages.success(request, 'Pago aprobado. Te enviamos el acceso al email de compra.')
        except Exception as exc:
            logger.error('Error confirmando pago MP ebook %s: %s', payment_id, exc)
            messages.warning(request, 'Pago recibido. Si el email demora, escribinos a soporte.')
    else:
        messages.info(request, 'Tu pago quedó pendiente de confirmación.')
    return redirect('core:ebook')


def _confirm_mp_ebook_payment(payment_id: str):
    import mercadopago

    sdk = mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))
    result = sdk.payment().get(payment_id)
    if result['status'] != 200:
        raise ValueError(f'MercadoPago payment GET falló: {result}')

    payment = result['response']
    if payment.get('status') != 'approved':
        return None

    external_reference = payment.get('external_reference', '')
    if not external_reference.startswith('ebook:'):
        return None

    slug = external_reference.split(':', 1)[1]
    ebook_obj = Ebook.objects.get(slug=slug, activo=True)
    payer = payment.get('payer') or {}
    buyer_email = (payer.get('email') or payment.get('metadata', {}).get('buyer_email') or '').lower().strip()
    if not buyer_email:
        raise ValueError('Pago MP ebook sin email de comprador')

    transaction = f'mp_{payment.get("id")}'
    order, created = EbookOrder.objects.update_or_create(
        hotmart_transaction=transaction,
        defaults={
            'status': 'approved',
            'hotmart_product_id': ebook_obj.hotmart_product_id,
            'hotmart_offer_code': 'mercadopago',
            'buyer_email': buyer_email,
            'buyer_name': payer.get('first_name', '') or payer.get('last_name', '') or buyer_email,
            'buyer_first_name': payer.get('first_name', ''),
            'buyer_last_name': payer.get('last_name', ''),
            'purchase_price': payment.get('transaction_amount'),
            'purchase_currency': payment.get('currency_id', ''),
            'hotmart_payload': payment,
            'approved_at': timezone.now(),
        },
    )

    if created:
        from core.services.email_service import send_welcome_ebook_email
        send_welcome_ebook_email(order)
    return order
