# Las vistas delegan la lógica a los controladores.
from core.controllers.inicio_controller import inicio
from core.controllers.habilidad_controller import lista_habilidades, detalle_habilidad
from core.controllers.ats_controller import (
    ats_landing, ats_evaluator, ats_resultado, ats_checkout, ats_informe_completo,
    ats_payment_create, ats_payment_success, ats_payment_cancel,
    webhook_stripe, webhook_mercadopago,
    descargar_pdf_reporte,
    PaymentSuccessView, check_payment_status,
    api_reenviar_email_reporte,
)
from core.controllers.hotmart_controller import webhook_hotmart
from core.controllers.stripe_webhook_controller import stripe_webhook
from core.controllers.mercadopago_webhook_controller import mercadopago_webhook
from core.controllers.payments_controller import create_payment_session, create_portal_session, auth_status
from core.controllers.unified_webhook_controller import unified_webhook
from core.controllers.mentor_ia_controller import (
    mentor_ia, mentor_ia_checkout, mentor_ia_checkout_start, mentor_ia_checkout_success, mentor_ia_checkout_cancel,
    mentor_ia_mp_checkout, mentor_ia_mp_checkout_start, mentor_ia_mp_checkout_success, mentor_ia_mp_checkout_cancel,
    mentor_ia_chat, mentor_ia_subscription, mentor_ia_mp_sync, mentor_ia_mp_cancel,
    mentor_ia_api_new_session, mentor_ia_api_send_message,
    webhook_stripe_mentoria,
)
from core.controllers.ebook_controller import ebook, ebook_mp_checkout, ebook_mp_success
from core.controllers.soft_skills_controller import soft_skills
from core.controllers.mentoring_controller import mentoring
from core.controllers.premium_controller import premium
from core.controllers.dashboard_controller import dashboard
from core.controllers.auth_controller import login_view, logout_view, google_oauth_login
from core.controllers.admin_controller import panel_admin
from core.controllers.roleplay_controller import (
    roleplay_list_scenarios, roleplay_start_session, roleplay_send_message,
    roleplay_selector, roleplay_chat_page, roleplay_get_session,
    roleplay_get_available_roles, roleplay_update_user_role, roleplay_regenerate_scenario,
)

__all__ = [
    'inicio', 'lista_habilidades', 'detalle_habilidad',
    'ats_landing', 'ats_evaluator', 'ats_resultado', 'ats_checkout', 'ats_informe_completo',
    'ats_payment_create', 'ats_payment_success', 'ats_payment_cancel',
    'webhook_stripe', 'webhook_mercadopago',
    'descargar_pdf_reporte',
    'PaymentSuccessView', 'check_payment_status', 'api_reenviar_email_reporte',
    'webhook_hotmart',
    'stripe_webhook',
    'mercadopago_webhook',
    'create_payment_session', 'create_portal_session', 'auth_status',
    'unified_webhook',
    'mentor_ia', 'mentor_ia_checkout', 'mentor_ia_checkout_start', 'mentor_ia_checkout_success', 'mentor_ia_checkout_cancel',
    'mentor_ia_mp_checkout', 'mentor_ia_mp_checkout_start', 'mentor_ia_mp_checkout_success', 'mentor_ia_mp_checkout_cancel',
    'mentor_ia_chat', 'mentor_ia_subscription', 'mentor_ia_mp_sync', 'mentor_ia_mp_cancel',
    'mentor_ia_api_new_session', 'mentor_ia_api_send_message',
    'webhook_stripe_mentoria',
    'ebook', 'ebook_mp_checkout', 'ebook_mp_success', 'soft_skills', 'mentoring', 'premium', 'dashboard',
    'login_view', 'logout_view', 'panel_admin',
    'roleplay_list_scenarios', 'roleplay_start_session', 'roleplay_send_message',
    'roleplay_selector', 'roleplay_chat_page', 'roleplay_get_session',
    'roleplay_get_available_roles', 'roleplay_update_user_role', 'roleplay_regenerate_scenario',
]

