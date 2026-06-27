from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

HERRAMIENTAS = [
    {'nombre': 'Evaluador ATS', 'descripcion': 'Analizá tu CV con IA', 'url': 'ats_evaluator', 'icon': '📄', 'color': 'blue'},
    {'nombre': 'Ebook Soft Skills', 'descripcion': 'Descargá el ebook gratuito', 'url': 'ebook', 'icon': '📚', 'color': 'green'},
    {'nombre': 'Evaluador Soft Skills', 'descripcion': 'Evaluá tus habilidades', 'url': 'soft_skills', 'icon': '🧠', 'color': 'purple'},
    {'nombre': 'Mentorías', 'descripcion': 'Reservá una sesión 1-a-1', 'url': 'mentoring', 'icon': '👥', 'color': 'orange'},
    {'nombre': 'Plan Premium', 'descripcion': 'Actualizá tu plan', 'url': 'premium', 'icon': '⭐', 'color': 'yellow'},
]

_solo_staff = user_passes_test(lambda u: u.is_active and u.is_staff, login_url='/login/')


@_solo_staff
def dashboard(request):
    return render(request, 'core/dashboard.html', {'herramientas': HERRAMIENTAS})

