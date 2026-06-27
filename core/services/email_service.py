"""
Servicio de email transaccional — proveedor: Resend (resend.com)

Instalación:  pip install resend
Variables de entorno requeridas:
  RESEND_API_KEY      → API key de Resend
  DEFAULT_FROM_EMAIL  → ej. "SkillsForIT <info@skillsforit.com>"

Variables opcionales (con defaults razonables):
  SITE_URL            → "https://skillsforit.com"
  SUPPORT_URL         → "https://skillsforit.com/soporte/"
  EBOOK_WELCOME_COUPON→ código de cupón enviado en el email de bienvenida
"""

import logging

import resend
from django.conf import settings
from django.template.loader import render_to_string

from core.models import EbookOrder

logger = logging.getLogger(__name__)

_FROM = getattr(settings, 'DEFAULT_FROM_EMAIL', 'SkillsForIT <info@skillsforit.com>')
_SITE_URL = getattr(settings, 'SITE_URL', 'https://skillsforit.com')
_SUPPORT_URL = getattr(settings, 'SUPPORT_URL', 'https://skillsforit.com/soporte/')
_COUPON = getattr(settings, 'EBOOK_WELCOME_COUPON', 'SKILLS20')


# ────────────────────────────────────────────────────────────────────────────
#  Helper interno
# ────────────────────────────────────────────────────────────────────────────

def _get_resend_client() -> bool:
    """Configura la API key de Resend y devuelve True si está disponible."""
    api_key = getattr(settings, 'RESEND_API_KEY', '')
    if not api_key:
        logger.error('RESEND_API_KEY no está configurado — email no enviado')
        return False
    resend.api_key = api_key
    return True


def _buyer_first_name(order: EbookOrder) -> str:
    """Extrae el primer nombre del comprador con fallback amigable."""
    if order.buyer_first_name:
        return order.buyer_first_name.strip().capitalize()
    if order.buyer_name:
        return order.buyer_name.strip().split()[0].capitalize()
    return 'allí'


def _product_name(order: EbookOrder) -> str:
    """Lee el nombre del producto desde el payload de Hotmart."""
    return (
        order.hotmart_payload
        .get('data', {})
        .get('product', {})
        .get('name', 'tu eBook')
    )


# ────────────────────────────────────────────────────────────────────────────
#  Email de bienvenida post-compra
# ────────────────────────────────────────────────────────────────────────────

def send_welcome_ebook_email(order: EbookOrder) -> bool:
    """
    Envía el correo de bienvenida al comprador de un eBook.

    Cuándo llamar: solo cuando la orden fue recién creada (created=True en
    update_or_create) para garantizar idempotencia y no spamear en reintentos
    del webhook de Hotmart.

    Retorna True si Resend aceptó el envío, False si hubo algún error.
    """
    if not _get_resend_client():
        return False

    context = {
        'first_name':   _buyer_first_name(order),
        'product_name': _product_name(order),
        'coupon_code':  _COUPON,
        'support_url':  _SUPPORT_URL,
        'site_url':     _SITE_URL,
    }

    html_body = render_to_string('core/emails/ebook_bienvenida.html', context)

    try:
        response = resend.Emails.send({
            'from':    _FROM,
            'to':      [order.buyer_email],
            'subject': f'¡Bienvenido/a a SkillsForIT! Tu "{context["product_name"]}" está listo 🎉',
            'html':    html_body,
        })
        email_id = response.get('id', 'n/a')
        logger.info(
            'Email de bienvenida enviado — buyer=%s transaction=%s resend_id=%s',
            order.buyer_email,
            order.hotmart_transaction,
            email_id,
        )
        return True

    except resend.exceptions.ResendError as exc:
        logger.error(
            'Resend API error enviando a %s (transaction=%s): %s',
            order.buyer_email,
            order.hotmart_transaction,
            exc,
        )
        return False

    except Exception as exc:
        logger.exception(
            'Error inesperado enviando email a %s (transaction=%s): %s',
            order.buyer_email,
            order.hotmart_transaction,
            exc,
        )
        return False
