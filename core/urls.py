from django.urls import path
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('ats/', views.ats_landing, name='ats_landing'),
    path('ats-evaluator/', views.ats_evaluator, name='ats_evaluator'),
    path('ats-evaluator/resultado/<uuid:uuid>/', views.ats_resultado, name='ats_resultado'),
    path('ats-evaluator/checkout/<uuid:uuid>/', views.ats_checkout, name='ats_checkout'),
    path('ats-evaluator/informe/<uuid:uuid>/', views.ats_informe_completo, name='ats_informe_completo'),
    path('ats-evaluator/informe/<uuid:uuid>/pdf/', views.descargar_pdf_reporte, name='ats_pdf'),
    # Pago: creación de sesión, retorno y cancelación
    path('ats-evaluator/checkout/<uuid:uuid>/pay/', views.ats_payment_create, name='ats_payment_create'),
    path('ats-evaluator/checkout/<uuid:uuid>/success/<str:gateway>/', views.ats_payment_success, name='ats_payment_success'),
    path('ats-evaluator/checkout/<uuid:uuid>/cancel/', views.ats_payment_cancel, name='ats_payment_cancel'),
    # Webhooks de pasarelas (CSRF exempt — validación interna)
    path('webhooks/stripe/', views.webhook_stripe, name='webhook_stripe'),
    path('webhooks/mercadopago/', views.webhook_mercadopago, name='webhook_mercadopago'),
    path('api/webhooks/hotmart/', views.webhook_hotmart, name='webhook_hotmart'),
    path('api/v1/auth/status', views.auth_status, name='auth_status'),
    path('api/v1/payments/create-session', views.create_payment_session, name='create_payment_session'),
    path('api/v1/payments/portal', views.create_portal_session, name='create_portal_session'),
    path('api/v1/webhooks/payments', views.unified_webhook, name='unified_webhook'),
    path('api/v1/webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('api/v1/webhooks/mercadopago/', views.mercadopago_webhook, name='mercadopago_webhook'),

    # MentorIA — MercadoPago checkout
    path('mentoria/mp/checkout/', views.mentor_ia_mp_checkout, name='mentor_ia_mp_checkout'),
    path('mentoria/mp/checkout/success/', views.mentor_ia_mp_checkout_success, name='mentor_ia_mp_checkout_success'),
    path('mentoria/mp/checkout/cancel/', views.mentor_ia_mp_checkout_cancel, name='mentor_ia_mp_checkout_cancel'),

    # MentorIA
    path('mentoria/',                          views.mentor_ia,                    name='mentor_ia'),
    path('mentoria/checkout/',                 views.mentor_ia_checkout,           name='mentor_ia_checkout'),
    path('mentoria/checkout/success/',         views.mentor_ia_checkout_success,   name='mentor_ia_checkout_success'),
    path('mentoria/checkout/cancel/',          views.mentor_ia_checkout_cancel,    name='mentor_ia_checkout_cancel'),
    path('mentoria/suscripcion/',                views.mentor_ia_subscription,        name='mentor_ia_subscription'),
    path('mentoria/mp/cancel/',                  views.mentor_ia_mp_cancel,           name='mentor_ia_mp_cancel'),
    path('mentoria/chat/',                       views.mentor_ia_chat,               name='mentor_ia_chat'),
    path('mentoria/api/session/',              views.mentor_ia_api_new_session,    name='mentor_ia_api_new_session'),
    path('mentoria/api/message/<uuid:session_id>/', views.mentor_ia_api_send_message, name='mentor_ia_api_send_message'),
    path('mentoria/api/webhook/',              views.webhook_stripe_mentoria,      name='webhook_stripe_mentoria'),

    # Roleplay de Soft Skills — páginas
    path('roleplay/',                               views.roleplay_selector,   name='roleplay_selector'),
    path('roleplay/chat/<uuid:session_id>/',        views.roleplay_chat_page,  name='roleplay_chat_page'),

    # Roleplay de Soft Skills — API
    path('api/v1/roleplay/scenarios/',                              views.roleplay_list_scenarios, name='roleplay_list_scenarios'),
    path('api/v1/roleplay/sessions/start/',                         views.roleplay_start_session,  name='roleplay_start_session'),
    path('api/v1/roleplay/sessions/<uuid:session_id>/',             views.roleplay_get_session,    name='roleplay_get_session'),
    path('api/v1/roleplay/sessions/<uuid:session_id>/message/',     views.roleplay_send_message,   name='roleplay_send_message'),
    path('api/v1/roleplay/roles/',                                  views.roleplay_get_available_roles, name='roleplay_get_available_roles'),
    path('api/v1/roleplay/profile/update-role/',                    views.roleplay_update_user_role,    name='roleplay_update_user_role'),
    # Página de confirmación de pago + polling de estado
    path('ats-evaluator/pago-exitoso/<uuid:report_id>/', views.PaymentSuccessView.as_view(), name='payment_success_page'),
    path('ats-evaluator/pago-exitoso/<uuid:report_id>/status/', views.check_payment_status, name='check_payment_status'),
    path('ats-evaluator/pago-exitoso/<uuid:report_id>/reenviar-email/', views.api_reenviar_email_reporte, name='api_reenviar_email_reporte'),
    path('ebook/', views.ebook, name='ebook'),
    # Soft Skills SPA — Django sirve el shell para / y todas las subrutas;
    # Vue Router maneja la navegación interna.
    path('soft-skills/', views.soft_skills, name='soft_skills'),
    path('soft-skills/<path:subpath>', views.soft_skills),
    path('mentoring/', views.mentoring, name='mentoring'),
    path('premium/', views.premium, name='premium'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('habilidades/', views.lista_habilidades, name='lista_habilidades'),
    path('habilidades/<int:pk>/', views.detalle_habilidad, name='detalle_habilidad'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('auth/google/', views.google_oauth_login, name='google_oauth_login'),

    # Panel de administrador
    path('admin/', views.panel_admin, name='panel_admin'),

    # Recuperación de contraseña
    path('password-reset/',
         PasswordResetView.as_view(
             template_name='core/auth/password_reset.html',
             email_template_name='core/auth/password_reset_email.html',
             html_email_template_name='core/auth/password_reset_email_html.html',
             subject_template_name='core/auth/password_reset_subject.txt',
             success_url='/password-reset/done/',
         ),
         name='password_reset'),
    path('password-reset/done/',
         PasswordResetDoneView.as_view(
             template_name='core/auth/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(
             template_name='core/auth/password_reset_confirm.html',
             success_url='/password-reset/complete/',
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         PasswordResetCompleteView.as_view(
             template_name='core/auth/password_reset_complete.html',
         ),
         name='password_reset_complete'),
]
