from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from core.models import MentoriaReserva, SuscripcionPremium

User = get_user_model()

_solo_admin = user_passes_test(lambda u: u.is_active and u.is_superuser, login_url='/login/')


@_solo_admin
def panel_admin(request):
    tab = request.GET.get('tab', 'resumen')

    context = {'tab': tab}

    if tab == 'resumen':
        context['stats'] = [
            {'label': 'Usuarios registrados',  'valor': User.objects.count(),               'icon': '👤', 'color': 'blue'},
            {'label': 'Mentorías reservadas',   'valor': MentoriaReserva.objects.count(),    'icon': '📅', 'color': 'orange'},
            {'label': 'Suscripciones Premium',  'valor': SuscripcionPremium.objects.count(), 'icon': '⭐', 'color': 'purple'},
            {'label': 'Mentorías pendientes',
             'valor': MentoriaReserva.objects.filter(estado='pendiente').count(),
             'icon': '⏳', 'color': 'yellow'},
        ]

    elif tab == 'usuarios':
        context['usuarios'] = User.objects.order_by('-created_at').values(
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_superuser', 'is_active', 'created_at', 'last_login'
        )

    elif tab == 'mentorias':
        context['reservas'] = MentoriaReserva.objects.select_related('mentor').order_by('-fecha_creacion')

    elif tab == 'premium':
        context['suscripciones'] = SuscripcionPremium.objects.order_by('-fecha_registro')

    return render(request, 'core/admin_panel.html', context)
