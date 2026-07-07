"""
Controlador del flujo ATS Evaluator.

Flujo completo:
  POST /ats-evaluator/                          → Agent 1 → crea AnalysisReport → redirect resultado
  GET  /ats-evaluator/resultado/<uuid>/         → vista gratuita (free_content)
  GET  /ats-evaluator/checkout/<uuid>/          → página de selección de moneda/pasarela
  POST /ats-evaluator/checkout/<uuid>/pay/      → crea sesión en Stripe o MP → redirect externo
  GET  /ats-evaluator/checkout/<uuid>/success/<gateway>/  → confirma pago → redirect informe
  GET  /ats-evaluator/checkout/<uuid>/cancel/   → vuelve al checkout
  GET  /ats-evaluator/informe/<uuid>/           → Agent 2 → vista paga (paid_content) + PDF
  POST /webhooks/stripe/                        → webhook Stripe
  POST /webhooks/mercadopago/                   → webhook MercadoPago IPN
"""

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import AnalysisReport
from core.services.ai_agents import run_agent1, run_agent2
from core.services.ats_engine import score_info, generar_recomendaciones
from core.services.payment_service import (
    create_checkout_session,
    confirm_payment,
    handle_stripe_webhook,
    handle_mercadopago_webhook,
    PRICE_USD,
    PRICE_ARS,
)

logger = logging.getLogger(__name__)

PRECIO_USD = PRICE_USD
PRECIO_ARS = PRICE_ARS


# ────────────────────────────────────────────────────────────────────────────
#  Helpers de lectura de PDF
# ────────────────────────────────────────────────────────────────────────────

def _extract_text_from_pdf(pdf_file) -> str:
    """
    Extrae texto plano del PDF subido.
    Intenta PyPDF2 primero; si no está instalado, usa el nombre del archivo
    como seed para el motor determinístico de fallback.
    """
    try:
        import PyPDF2  # noqa: PLC0415
        reader = PyPDF2.PdfReader(pdf_file)
        pages = [page.extract_text() or '' for page in reader.pages]
        return '\n'.join(pages).strip()
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: usa el nombre del archivo (el motor determinístico lo usa como seed)
    pdf_file.seek(0)
    return pdf_file.name


# ────────────────────────────────────────────────────────────────────────────
#  View 1 — Formulario de carga + Agent 1
# ────────────────────────────────────────────────────────────────────────────

def ats_landing(request):
    return render(request, 'core/ats_landing.html', {'precio_usd': PRECIO_USD})


def ats_evaluator(request):
    if request.method == 'POST':
        cv_file  = request.FILES.get('cv')
        jd_texto = request.POST.get('jd_texto', '').strip()

        if not cv_file:
            messages.error(request, 'Por favor seleccioná un archivo PDF.')
            return render(request, 'core/ats_evaluator.html')

        if not (cv_file.content_type == 'application/pdf'
                or cv_file.name.lower().endswith('.pdf')):
            messages.error(request, 'Solo se aceptan archivos PDF.')
            return render(request, 'core/ats_evaluator.html')

        cv_raw_text   = _extract_text_from_pdf(cv_file)
        agent1_result = run_agent1(cv_raw_text, jd_texto)
        free_content  = agent1_result['free_content']

        # Generate deterministic basic recommendations for the free tier
        keywords_missing = free_content.get('keyword_match', {}).get('missing', [])
        section_check    = free_content.get('section_check', {})
        sections_missing = [s for s, ok in section_check.items() if not ok]
        parsing_issues   = free_content.get('parsing_issues', [])
        free_content['basic_fixes'] = generar_recomendaciones(
            keywords_missing, sections_missing, parsing_issues
        )

        report = AnalysisReport.objects.create(
            user            = request.user if request.user.is_authenticated else None,
            cv_raw_text     = cv_raw_text,
            job_description = jd_texto,
            ats_score       = agent1_result['ats_score'],
            free_content    = free_content,
            is_paid         = False,
        )

        return redirect('core:ats_resultado', uuid=str(report.id))

    return render(request, 'core/ats_evaluator.html')


# ────────────────────────────────────────────────────────────────────────────
#  View 2 — Resultado gratuito
# ────────────────────────────────────────────────────────────────────────────

def ats_resultado(request, uuid):
    report = get_object_or_404(AnalysisReport, pk=uuid)
    info   = score_info(report.ats_score)

    # Use basic_fixes from free_content (generated deterministically after agent1)
    # Fallback to paid_content fixes for legacy reports
    basic_fixes = (
        report.free_content.get('basic_fixes')
        or report.paid_content.get('actionable_fixes', [])
    )
    score_proyectado = min(report.ats_score + len(basic_fixes) * 2, 95)

    return render(request, 'core/ats_resultado.html', {
        'report':           report,
        'score_info':       info,
        'actionable_fixes': basic_fixes,
        'score_proyectado': score_proyectado,
        'analisis':         _compat_analisis(report),
        'precio_usd':       PRECIO_USD,
        'precio_ars':       PRECIO_ARS,
    })


# ────────────────────────────────────────────────────────────────────────────
#  View 3 — Checkout (selección de moneda / pasarela)
# ────────────────────────────────────────────────────────────────────────────

def ats_checkout(request, uuid):
    report = get_object_or_404(AnalysisReport, pk=uuid)

    if report.is_paid:
        return redirect('core:ats_informe_completo', uuid=uuid)

    return render(request, 'core/ats_checkout.html', {
        'report':     report,
        'precio_usd': PRECIO_USD,
        'precio_ars': PRECIO_ARS,
        'analisis':   _compat_analisis(report),
    })


# ────────────────────────────────────────────────────────────────────────────
#  View 3b — Crear sesión de pago en la pasarela
# ────────────────────────────────────────────────────────────────────────────

@require_POST
def ats_payment_create(request, uuid):
    """
    Recibe currency ('USD', 'ARS', 'BRL') y email del comprador,
    luego redirige al checkout de la pasarela.
    """
    report   = get_object_or_404(AnalysisReport, pk=uuid)
    currency = request.POST.get('currency', 'USD').upper()
    email    = request.POST.get('email', '').strip()

    if report.is_paid:
        return redirect('core:ats_informe_completo', uuid=uuid)

    if currency not in ('USD', 'ARS', 'BRL'):
        messages.error(request, 'Moneda no válida.')
        return redirect('core:ats_checkout', uuid=uuid)

    # Persist email in session to use it in payment_success
    if email:
        request.session[f'ats_email_{uuid}'] = email

    try:
        gateway_url = create_checkout_session(report, currency, request)
        return redirect(gateway_url)
    except Exception as exc:
        logger.error('Error creando sesión de pago: %s', exc)
        messages.error(request, 'Hubo un error al procesar el pago. Intentá de nuevo.')
        return redirect('core:ats_checkout', uuid=uuid)


# ────────────────────────────────────────────────────────────────────────────
#  View 3c — Retorno exitoso desde la pasarela
# ────────────────────────────────────────────────────────────────────────────

def ats_payment_success(request, uuid, gateway):
    """
    URL de retorno después de un pago aprobado.
    Stripe pasa ?session_id=...; MercadoPago pasa ?payment_id=...&status=...
    """
    report = get_object_or_404(AnalysisReport, pk=uuid)

    if not report.is_paid:
        if gateway == 'stripe':
            payment_id = request.GET.get('session_id', f'stripe_{uuid}')
        else:
            payment_id = request.GET.get('payment_id', f'mp_{uuid}')
            status     = request.GET.get('status', 'approved')
            if status != 'approved':
                messages.warning(request, 'Tu pago está pendiente de acreditación.')
                return redirect('core:ats_checkout', uuid=uuid)

        confirm_payment(report, gateway, payment_id)

        # Send confirmation email (non-blocking best-effort)
        buyer_email = (
            request.session.pop(f'ats_email_{uuid}', '')
            or (report.user.email if report.user_id else '')
        )
        if buyer_email:
            try:
                from core.services.payment_service import enviar_email_reporte_premium
                enviar_email_reporte_premium(report, buyer_email)
            except Exception as exc:
                logger.warning('Email send failed after payment: %s', exc)

    return redirect('core:ats_informe_completo', uuid=str(report.id))


# ────────────────────────────────────────────────────────────────────────────
#  View 3d — Cancelación de pago
# ────────────────────────────────────────────────────────────────────────────

def ats_payment_cancel(request, uuid):
    messages.info(request, 'Cancelaste el proceso de pago. Podés intentarlo cuando quieras.')
    return redirect('core:ats_checkout', uuid=uuid)


# ────────────────────────────────────────────────────────────────────────────
#  Webhooks
# ────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def webhook_stripe(request):
    payload    = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        handle_stripe_webhook(payload, sig_header)
        return JsonResponse({'status': 'ok'})
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)
    except Exception as exc:
        logger.error('Stripe webhook unhandled: %s', exc)
        return HttpResponse('error', status=500)


@csrf_exempt
def webhook_mercadopago(request):
    params = {**request.GET.dict(), **request.POST.dict()}
    try:
        handle_mercadopago_webhook(params)
        return JsonResponse({'status': 'ok'})
    except Exception as exc:
        logger.error('MercadoPago webhook unhandled: %s', exc)
        return HttpResponse('error', status=500)



# ────────────────────────────────────────────────────────────────────────────
#  View 4 — Informe completo (Agent 2, solo si is_paid)
# ────────────────────────────────────────────────────────────────────────────

def ats_informe_completo(request, uuid):
    report = get_object_or_404(AnalysisReport, pk=uuid)

    if not report.is_paid:
        return redirect('core:ats_checkout', uuid=uuid)

    # Run premium agent2 lazily — only if paid_content is empty or lacks section_analysis
    if not report.paid_content or 'section_analysis' not in report.paid_content:
        agent2_result = run_agent2(
            report.cv_raw_text,
            report.job_description or '',
            report.free_content,
        )
        report.paid_content = agent2_result['paid_content']
        report.save(update_fields=['paid_content'])

    info    = score_info(report.ats_score)
    paid    = report.paid_content

    actionable_fixes    = paid.get('actionable_fixes', [])
    section_analysis    = paid.get('section_analysis', [])
    keyword_integration = paid.get('keyword_integration', [])
    score_proyectado    = min(report.ats_score + len(actionable_fixes) * 2, 95)

    return render(request, 'core/ats_informe_completo.html', {
        'report':              report,
        'score_info':          info,
        'tailored_summary':    paid.get('tailored_summary', ''),
        'section_analysis':    section_analysis,
        'keyword_integration': keyword_integration,
        'actionable_fixes':    actionable_fixes,
        'score_proyectado':    score_proyectado,
        'analisis':            _compat_analisis(report),
        'precio_usd':          PRECIO_USD,
    })


# ────────────────────────────────────────────────────────────────────────────
#  Adaptador de compatibilidad con templates existentes
# ────────────────────────────────────────────────────────────────────────────

def _compat_analisis(report: AnalysisReport) -> dict:
    """
    Mapea AnalysisReport al formato que usan los templates heredados
    (ats_resultado.html, ats_checkout.html, ats_informe_completo.html).
    Permite que los templates sigan funcionando sin reescribirlos.
    """
    section_check = report.section_check
    secciones_presentes = [k for k, v in section_check.items() if v]
    secciones_faltantes = [k for k, v in section_check.items() if not v]

    return {
        'id':                   str(report.id),
        'archivo_nombre':       f'cv_{str(report.id)[:8]}.pdf',
        'score_ats':            report.ats_score,
        'legibilidad_ok':       len(report.parsing_issues) == 0,
        'problemas_formato':    report.parsing_issues,
        'keywords_encontradas': report.keywords_found,
        'keywords_faltantes':   report.keywords_missing,
        'secciones_presentes':  secciones_presentes,
        'secciones_faltantes':  secciones_faltantes,
        'pagado':               report.is_paid,
        'metodo_pago':          report.payment_gateway,
        'jd_texto':             report.job_description,
    }


def _fixes_to_recs(fixes: list) -> list:
    """Convierte actionable_fixes al formato de recomendaciones del template."""
    result = []
    for fix in fixes:
        result.append({
            'tipo':        'seccion',
            'icono':       '🔧',
            'titulo':      fix.get('section', 'Mejora'),
            'descripcion': fix.get('reason', ''),
            'accion':      fix.get('suggested_text', ''),
            'ejemplo':     fix.get('suggested_text', ''),
        })
    return result


# ────────────────────────────────────────────────────────────────────────────
#  Descarga de PDF con ReportLab
# ────────────────────────────────────────────────────────────────────────────

def descargar_pdf_reporte(request, uuid):
    """
    GET /ats-evaluator/informe/<uuid>/pdf/

    Genera y descarga el informe completo en PDF usando ReportLab.
    Requiere que el reporte esté pagado (is_paid=True).
    Si ReportLab no está instalado retorna 501 con instrucciones.
    """
    from django.http import FileResponse  # noqa: PLC0415
    from io import BytesIO                # noqa: PLC0415

    report = get_object_or_404(AnalysisReport, pk=uuid)

    if not report.is_paid:
        return HttpResponse('No has adquirido este informe.', status=403)

    # Si paid_content está vacío, disparamos el Agent 2 on-demand
    if not report.paid_content:
        from core.services.payment_service import ejecutar_agente_ia_premium  # noqa: PLC0415
        ejecutar_agente_ia_premium(report)
        report.refresh_from_db(fields=['paid_content'])

    try:
        from reportlab.lib.pagesizes import letter              # noqa: PLC0415
        from reportlab.lib import colors                        # noqa: PLC0415
        from reportlab.platypus import (                        # noqa: PLC0415
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # noqa: PLC0415
    except ImportError:
        return HttpResponse(
            'ReportLab no está instalado. Ejecuta: pip install reportlab',
            status=501,
        )

    # ── Buffer en memoria ───────────────────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40,
    )

    # ── Estilos ─────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontSize=24, leading=28,
        textColor=colors.HexColor('#1E293B'), spaceAfter=15,
    )
    style_subtitle = ParagraphStyle(
        'SubTitleStyle', parent=styles['Heading2'],
        fontSize=14, leading=18,
        textColor=colors.HexColor('#475569'), spaceBefore=10, spaceAfter=10,
    )
    style_body = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'],
        fontSize=10, leading=14,
        textColor=colors.HexColor('#334155'), spaceAfter=8,
    )
    style_callout = ParagraphStyle(
        'CalloutStyle', parent=styles['Normal'],
        fontSize=10, leading=14,
        textColor=colors.HexColor('#0F172A'),
        backColor=colors.HexColor('#F1F5F9'),
        borderColor=colors.HexColor('#CBD5E1'),
        borderWidth=1, borderPadding=10, spaceBefore=10, spaceAfter=15,
    )

    story = []

    # ── Encabezado ─────────────────────────────────────────────────────────────
    story.append(Paragraph('Informe de Optimización de CV con IA', style_title))
    story.append(Paragraph(
        f'Puntaje ATS Alcanzado: <b>{report.ats_score}/100</b>', style_subtitle,
    ))
    story.append(Spacer(1, 15))

    # ── Resumen profesional (paid_content.tailored_summary) ───────────────
    story.append(Paragraph('1. Resumen Perfil Profesional Optimizado', style_subtitle))
    summary = report.paid_content.get('tailored_summary', 'No disponible.')
    story.append(Paragraph(summary, style_callout))
    story.append(Spacer(1, 10))

    # ── Correcciones accionables (paid_content.actionable_fixes) ────────
    story.append(Paragraph('2. Plan de Acción y Correcciones Detalladas', style_subtitle))
    story.append(Paragraph(
        'Reescribí las siguientes secciones de tu experiencia para maximizar '
        'el impacto frente al ATS:',
        style_body,
    ))
    story.append(Spacer(1, 10))

    fixes = report.paid_content.get('actionable_fixes', [])

    if fixes:
        table_data = [[
            Paragraph('<b>Sección / Contexto</b>', style_body),
            Paragraph('<b>Tu redacción original</b>', style_body),
            Paragraph('<b>Propuesta Optimizada por IA</b>', style_body),
        ]]
        for fix in fixes:
            table_data.append([
                Paragraph(
                    f"<b>{fix.get('section', '')}</b><br/><br/>"
                    f"<font color='#64748B'>{fix.get('reason', '')}</font>",
                    style_body,
                ),
                Paragraph(fix.get('current_text', ''), style_body),
                Paragraph(f"<b>{fix.get('suggested_text', '')}</b>", style_body),
            ])

        fixes_table = Table(table_data, colWidths=[130, 200, 200])
        fixes_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#1E293B')),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  8),
            ('TOPPADDING',    (0, 0), (-1, 0),  8),
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND',    (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ]))
        story.append(fixes_table)
    else:
        story.append(Paragraph('No hay correcciones disponibles.', style_body))

    # ── Construir y devolver ─────────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'Informe_Optimizado_ATS_{str(uuid)[:8]}.pdf',
        content_type='application/pdf',
    )


# ────────────────────────────────────────────────────────────────────────────
#  PaymentSuccessView
#  Página de confirmación de pago. Muestra el estado del reporte al usuario
#  cuando regresa desde la pasarela externa (Stripe / MercadoPago).
#
#  El webhook puede llegar antes o después del redirect del usuario.
#  Para manejar esa carrera se expone check_payment_status como endpoint
#  de polling ligero desde el frontend.
# ────────────────────────────────────────────────────────────────────────────

from django.views.generic import TemplateView  # noqa: E402


class PaymentSuccessView(TemplateView):
    """
    Vista genérica de éxito de pago.

    Recibe al usuario cuando regresa de la pasarela.
    Lee el parámetro ?success=true (informativo) y comprueba si la base de
    datos ya fue impactada por el webhook (is_paid=True).

    URL: GET /ats-evaluator/pago-exitoso/<uuid:report_id>/
    Template: core/ats_payment_success_page.html
    """
    template_name = 'core/ats_payment_success_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_id = self.kwargs.get('report_id')
        report = get_object_or_404(AnalysisReport, id=report_id)

        context['report'] = report
        # Email del usuario si está registrado, o placeholder amigable
        context['user_email'] = (
            report.user.email if report.user_id else 'tu correo registrado'
        )
        # Indica si el webhook ya procesó el pago (útil para el template)
        context['pago_confirmado'] = report.is_paid
        return context


def check_payment_status(request, report_id):
    """
    Endpoint de polling ligero para el frontend.

    Permite que el JS de la página de éxito pregunte cada pocos segundos si
    el webhook ya marcó el pago y si el Agent 2 ya generó el contenido premium.

    GET /ats-evaluator/pago-exitoso/<uuid:report_id>/status/
    Respuesta: {"is_paid": true, "has_premium_content": true}
    """
    report = get_object_or_404(AnalysisReport, id=report_id)
    return JsonResponse({
        'is_paid':             report.is_paid,
        'has_premium_content': bool(report.paid_content),
    })


# ────────────────────────────────────────────────────────────────────────────
#  api_reenviar_email_reporte
#  Re-envía el email de agradecimiento con el informe bajo demanda (botón UX).
# ────────────────────────────────────────────────────────────────────────────

@require_POST
def api_reenviar_email_reporte(request, report_id):
    """
    POST /ats-evaluator/pago-exitoso/<uuid:report_id>/reenviar-email/

    Dispara nuevamente el email de agradecimiento con el link de descarga.
    Útil cuando el usuario no recibió el mail inicial (spam, demora, etc.).

    Respuestas:
      200  {"ok": true}                       — email enviado
      400  {"error": "Reporte no pagado"}      — intento sin pago confirmado
      404  (get_object_or_404)                 — reporte inexistente
      500  {"error": "..."}                    — fallo de envío
    """
    from core.services.payment_service import (
        enviar_email_reporte_premium,
        ejecutar_agente_ia_premium,
    )  # noqa: PLC0415

    report = get_object_or_404(AnalysisReport, id=report_id)

    if not report.is_paid:
        return JsonResponse({'error': 'Reporte no pagado'}, status=400)

    # Asegurar que paid_content exista antes de enviar
    if not report.paid_content:
        ejecutar_agente_ia_premium(report)
        report.refresh_from_db(fields=['paid_content'])

    user_email = getattr(report.user, 'email', '') if report.user_id else ''
    if not user_email:
        return JsonResponse({'error': 'No hay email asociado a este reporte'}, status=400)

    enviado = enviar_email_reporte_premium(report, user_email)
    if enviado:
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'No se pudo enviar el email'}, status=500)

