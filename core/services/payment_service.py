"""
Servicio de pagos para el flujo ATS Evaluator.

Integra Stripe (USD) y MercadoPago (ARS/BRL) para el checkout del informe.
"""

import logging
import stripe
from django.conf import settings

logger = logging.getLogger(__name__)

PRICE_USD = '4.99'
PRICE_ARS = '4990'


# ────────────────────────────────────────────────────────────────────────────
#  Checkout
# ────────────────────────────────────────────────────────────────────────────

def create_checkout_session(report, currency: str, request) -> str:
    """
    Crea una sesión de checkout en Stripe (USD) o MercadoPago (ARS/BRL).
    Devuelve la URL de redirección a la pasarela.
    """
    site_url = getattr(settings, 'SITE_URL', 'https://skillsforit.online')
    success_url = f'{site_url}/ats-evaluator/checkout/{report.id}/success/{{gateway}}/'
    cancel_url  = f'{site_url}/ats-evaluator/checkout/{report.id}/cancel/'

    if currency == 'USD':
        return _stripe_checkout(report, site_url, success_url.replace('{gateway}', 'stripe'), cancel_url)
    else:
        return _mp_checkout(report, site_url, success_url.replace('{gateway}', 'mercadopago'), cancel_url, currency)


def _stripe_checkout(report, site_url: str, success_url: str, cancel_url: str) -> str:
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    price_id = getattr(settings, 'STRIPE_ATS_PRICE_ID', '')

    if not price_id:
        raise ValueError('STRIPE_ATS_PRICE_ID no configurado')

    params = {
        'mode':         'payment',
        'line_items':   [{'price': price_id, 'quantity': 1}],
        'success_url':  success_url + '?session_id={CHECKOUT_SESSION_ID}',
        'cancel_url':   cancel_url,
        'metadata':     {'report_id': str(report.id)},
    }
    if getattr(report, 'user', None) and report.user:
        params['customer_email'] = report.user.email

    session = stripe.checkout.Session.create(**params)
    return session.url


def _mp_checkout(report, site_url: str, success_url: str, cancel_url: str, currency: str) -> str:
    import mercadopago
    sdk = mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))

    amount = float(PRICE_ARS) if currency == 'ARS' else float('4.99')

    preference_data = {
        'items': [{
            'title':      'Informe ATS Evaluator — SkillsForIT',
            'quantity':   1,
            'unit_price': amount,
            'currency_id': currency,
        }],
        'back_urls': {
            'success': success_url,
            'failure': cancel_url,
            'pending': cancel_url,
        },
        'auto_return': 'approved',
        'external_reference': str(report.id),
    }

    result = sdk.preference().create(preference_data)
    if result['status'] not in (200, 201):
        raise ValueError(f"MercadoPago error: {result.get('response', {})}")

    return result['response']['init_point']


# ────────────────────────────────────────────────────────────────────────────
#  Confirmar pago
# ────────────────────────────────────────────────────────────────────────────

def confirm_payment(report, gateway: str, payment_id: str) -> None:
    """Marca el reporte como pagado y registra la pasarela."""
    report.is_paid         = True
    report.payment_gateway = gateway
    report.payment_id      = payment_id
    report.save(update_fields=['is_paid', 'payment_gateway', 'payment_id'])
    logger.info('ATS payment confirmed: report=%s gateway=%s', report.id, gateway)


# ────────────────────────────────────────────────────────────────────────────
#  Webhooks
# ────────────────────────────────────────────────────────────────────────────

def handle_stripe_webhook(payload: bytes, sig_header: str) -> None:
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    stripe.api_key  = getattr(settings, 'STRIPE_SECRET_KEY', '')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise ValueError(f'Invalid Stripe signature: {exc}') from exc

    event_type = event['type']
    data       = event['data']['object']

    if event_type == 'checkout.session.completed':
        report_id  = data.get('metadata', {}).get('report_id', '')
        payment_id = data.get('id', '')
        _apply_stripe_payment(report_id, payment_id)

    logger.info('Stripe webhook processed: %s', event_type)


def _apply_stripe_payment(report_id: str, payment_id: str) -> None:
    from core.models import AnalysisReport
    try:
        report = AnalysisReport.objects.get(pk=report_id)
        if not report.is_paid:
            confirm_payment(report, 'stripe', payment_id)
    except AnalysisReport.DoesNotExist:
        logger.error('Stripe webhook: report not found: %s', report_id)


def handle_mercadopago_webhook(params: dict) -> None:
    topic  = params.get('topic', '') or params.get('type', '')
    obj_id = params.get('id', '') or params.get('data.id', '')

    if topic not in ('payment', 'merchant_order'):
        return

    try:
        import mercadopago
        sdk = mercadopago.SDK(getattr(settings, 'MP_ACCESS_TOKEN', ''))
        result = sdk.payment().get(obj_id)
        if result['status'] != 200:
            return

        payment = result['response']
        if payment.get('status') != 'approved':
            return

        report_id  = payment.get('external_reference', '')
        payment_id = str(payment.get('id', ''))
        if report_id.startswith('ebook:'):
            from core.controllers.ebook_controller import _confirm_mp_ebook_payment
            _confirm_mp_ebook_payment(payment_id)
            return
        _apply_mp_payment(report_id, payment_id)

    except Exception as exc:
        logger.error('MP webhook error: %s', exc)


def _apply_mp_payment(report_id: str, payment_id: str) -> None:
    from core.models import AnalysisReport
    try:
        report = AnalysisReport.objects.get(pk=report_id)
        if not report.is_paid:
            confirm_payment(report, 'mercadopago', payment_id)
    except AnalysisReport.DoesNotExist:
        logger.error('MP webhook: report not found: %s', report_id)


# ────────────────────────────────────────────────────────────────────────────
#  Agent 2 on-demand y email
# ────────────────────────────────────────────────────────────────────────────

def ejecutar_agente_ia_premium(report) -> None:
    """Llama a run_agent2 y guarda paid_content en el reporte."""
    from core.services.ai_agents import run_agent2
    result = run_agent2(report.cv_raw_text, report.job_description or '', report.free_content)
    report.paid_content = result['paid_content']
    report.save(update_fields=['paid_content'])


def enviar_email_reporte_premium(report, user_email: str) -> bool:
    """Envía el email de acceso al informe premium. Devuelve True si tuvo éxito."""
    try:
        from core.services.email_service import send_report_email
        return send_report_email(report, user_email)
    except Exception as exc:
        logger.error('Error enviando email reporte: %s', exc)
        return False
