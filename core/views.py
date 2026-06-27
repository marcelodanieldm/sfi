# Las vistas delegan la lógica a los controladores.
from core.controllers.inicio_controller import inicio
from core.controllers.habilidad_controller import lista_habilidades, detalle_habilidad
from core.controllers.ats_controller import (
    ats_evaluator, ats_resultado, ats_checkout, ats_informe_completo,
    ats_payment_create, ats_payment_success, ats_payment_cancel,
    webhook_stripe, webhook_mercadopago,
    descargar_pdf_reporte,
    PaymentSuccessView, check_payment_status,
    api_reenviar_email_reporte,
)
from core.controllers.hotmart_controller import webhook_hotmart
from core.controllers.ebook_controller import ebook
from core.controllers.soft_skills_controller import soft_skills
from core.controllers.mentoring_controller import mentoring
from core.controllers.premium_controller import premium
from core.controllers.dashboard_controller import dashboard
from core.controllers.auth_controller import login_view, logout_view
from core.controllers.admin_controller import panel_admin

__all__ = [
    'inicio', 'lista_habilidades', 'detalle_habilidad',
    'ats_evaluator', 'ats_resultado', 'ats_checkout', 'ats_informe_completo',
    'ats_payment_create', 'ats_payment_success', 'ats_payment_cancel',
    'webhook_stripe', 'webhook_mercadopago',
    'descargar_pdf_reporte',
    'PaymentSuccessView', 'check_payment_status', 'api_reenviar_email_reporte',
    'webhook_hotmart',
    'ebook', 'soft_skills', 'mentoring', 'premium', 'dashboard',
    'login_view', 'logout_view', 'panel_admin',
]

