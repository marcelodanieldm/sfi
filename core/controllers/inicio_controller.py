from django.shortcuts import render


PRODUCTOS = [
    {
        'titulo': 'Evaluador ATS',
        'descripcion': 'Subí tu CV en PDF y recibí un análisis completo de compatibilidad con sistemas ATS, con recomendaciones concretas para mejorar.',
        'url': 'ats_evaluator',
        'icon': '📄',
        'color': 'blue',
    },
    {
        'titulo': 'Ebook Soft Skills',
        'descripcion': 'Descargá nuestro ebook gratuito con estrategias para mejorar tus habilidades blandas en entrevistas y el día a día en IT.',
        'url': 'ebook',
        'icon': '📚',
        'color': 'green',
    },
    {
        'titulo': 'Evaluador de Soft Skills',
        'descripcion': 'Respondé 5 situaciones reales del mundo del desarrollo de software y recibí un informe detallado de tus fortalezas y áreas de mejora.',
        'url': 'soft_skills',
        'icon': '🧠',
        'color': 'purple',
    },
    {
        'titulo': 'Plan Premium',
        'descripcion': 'Accedé a funcionalidades exclusivas: evaluaciones ilimitadas, mentorías prioritarias y contenido avanzado.',
        'url': 'premium',
        'icon': '⭐',
        'color': 'yellow',
    },
    {
        'titulo': 'Mentorías IT',
        'descripcion': 'Reservá sesiones 1-a-1 con mentores expertos en desarrollo de software, liderazgo técnico y crecimiento profesional.',
        'url': 'mentoring',
        'icon': '👥',
        'color': 'orange',
    },
]

STATS = [
    {'numero': '2,500+', 'label': 'CVs evaluados'},
    {'numero': '95%', 'label': 'Satisfacción'},
    {'numero': '300+', 'label': 'Mentorías realizadas'},
    {'numero': '50+', 'label': 'Mentores expertos'},
]


def inicio(request):
    return render(request, 'core/inicio.html', {
        'stats': STATS,
        'productos': PRODUCTOS,
    })

