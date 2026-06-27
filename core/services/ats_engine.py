import random
import hashlib
import re

KEYWORDS_TECH = [
    'Python', 'JavaScript', 'TypeScript', 'React', 'Vue.js', 'Angular',
    'Django', 'FastAPI', 'Node.js', 'Express', 'Spring Boot',
    'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
    'Git', 'GitHub', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
    'CI/CD', 'Jenkins', 'GitHub Actions', 'Agile', 'Scrum', 'Kanban', 'Jira',
    'REST API', 'GraphQL', 'Microservices', 'Linux', 'Bash',
    'Machine Learning', 'TensorFlow', 'Data Analysis', 'Pandas',
    'HTML', 'CSS', 'Tailwind', 'Testing', 'TDD', 'Jest',
    'Java', 'C#', '.NET', 'Go', 'DevOps', 'Terraform', 'Ansible',
]

SECCIONES_REQUERIDAS = [
    'Experiencia Laboral',
    'Educación',
    'Habilidades Técnicas',
    'Proyectos',
    'Certificaciones',
    'Perfil Profesional',
]

PROBLEMAS_FORMATO = [
    'Tabla detectada en sección de experiencia — los ATS no parsean tablas correctamente',
    'Diseño en 2 columnas — el texto se lee en orden incorrecto por los ATS',
    'Encabezado con fuente decorativa o ícono — usar solo texto plano',
    'Sección de habilidades con barras de progreso gráficas — reemplazar con lista de texto',
    'Imagen de foto de perfil embebida — los ATS la ignoran o generan errores de lectura',
]

REDACCIONES_SUGERIDAS = {
    'Perfil Profesional': (
        'Desarrollador/a de software con X años de experiencia en backend/frontend/fullstack. '
        'Especializado/a en el diseño y desarrollo de aplicaciones escalables. '
        'Trabajo orientado a resultados con fuerte capacidad de colaboración en equipos ágiles.'
    ),
    'Experiencia Laboral': (
        '• Desarrollé e implementé [funcionalidad] usando [tecnología], '
        'reduciendo [tiempo/errores] en un X%.\n'
        '• Lideré la migración de [sistema A] a [sistema B], '
        'impactando a N usuarios activos.\n'
        '• Participé en sprints de 2 semanas (Scrum), '
        'entregando features con cobertura de tests >80%.'
    ),
    'Habilidades Técnicas': (
        'Lenguajes: Python, JavaScript, TypeScript\n'
        'Frameworks: Django, React, Node.js\n'
        'Bases de datos: PostgreSQL, MongoDB\n'
        'DevOps: Docker, CI/CD, AWS\n'
        'Metodologías: Agile, Scrum, TDD'
    ),
    'Proyectos': (
        'Nombre del Proyecto | [Tecnologías usadas] | github.com/usuario/repo\n'
        'Descripción breve de qué hace el proyecto y el impacto que tuvo.\n'
        '• Implementé [feature] que resolvió [problema].\n'
        '• Stack: Python, Django, PostgreSQL, Docker.'
    ),
    'Educación': (
        'Título de Grado / Tecnicatura — Nombre de la Institución\n'
        'Año de inicio — Año de egreso (o "En curso")\n'
        'Optativo: promedio, materias relevantes, trabajos finales.'
    ),
    'Certificaciones': (
        '• AWS Certified Developer – Associate | Amazon Web Services | 2024\n'
        '• Professional Scrum Master I (PSM I) | Scrum.org | 2023\n'
        '• Python for Data Science | Coursera / edX | 2023'
    ),
}


def analizar_cv(nombre_archivo: str, jd_texto: str = '') -> dict:
    seed = int(hashlib.md5(nombre_archivo.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    score = rng.randint(44, 78)
    if jd_texto.strip():
        score = min(score + rng.randint(2, 7), 83)

    pool = KEYWORDS_TECH[:]
    rng.shuffle(pool)
    n_found = rng.randint(7, 15)
    keywords_encontradas = sorted(pool[:n_found])
    keywords_faltantes = sorted(pool[n_found:n_found + rng.randint(6, 11)])

    if jd_texto:
        jd_words = list(set(re.findall(r'\b[A-Z][a-zA-Z+#\.]{2,}\b', jd_texto)))[:8]
        keywords_faltantes = sorted(list(set(keywords_faltantes + jd_words)))[:12]

    secciones_pool = SECCIONES_REQUERIDAS[:]
    rng.shuffle(secciones_pool)
    n_presentes = rng.randint(3, 5)
    secciones_presentes = sorted(secciones_pool[:n_presentes])
    secciones_faltantes = sorted(secciones_pool[n_presentes:])

    n_problemas = rng.randint(0, 2)
    problemas_formato = rng.sample(PROBLEMAS_FORMATO, n_problemas)
    legibilidad_ok = n_problemas == 0

    return {
        'score_ats': score,
        'legibilidad_ok': legibilidad_ok,
        'problemas_formato': problemas_formato,
        'keywords_encontradas': keywords_encontradas,
        'keywords_faltantes': keywords_faltantes,
        'secciones_presentes': secciones_presentes,
        'secciones_faltantes': secciones_faltantes,
    }


def generar_recomendaciones(keywords_faltantes: list, secciones_faltantes: list,
                            problemas_formato: list) -> list:
    recs = []

    for problema in problemas_formato:
        recs.append({
            'tipo': 'formato',
            'icono': '⚠️',
            'titulo': 'Problema de formato crítico',
            'descripcion': problema,
            'accion': (
                'Convertí tu CV a formato de una sola columna con texto plano. '
                'Evitá tablas, gráficos y fuentes decorativas. '
                'Usá un template simple en Word o Google Docs.'
            ),
            'ejemplo': (
                'Antes: diseño con 2 columnas, tabla de habilidades con iconos\n'
                'Después: texto en una sola columna, habilidades listadas como texto'
            ),
        })

    for seccion in secciones_faltantes:
        template = REDACCIONES_SUGERIDAS.get(seccion, f'Incluir la sección "{seccion}" con ese título exacto.')
        recs.append({
            'tipo': 'seccion',
            'icono': '📋',
            'titulo': f'Sección faltante: {seccion}',
            'descripcion': (
                f'La sección "{seccion}" no fue detectada por el ATS. '
                'Los sistemas ATS buscan estos títulos de forma literal.'
            ),
            'accion': (
                f'Agregá la sección con el título exacto "{seccion}". '
                'No uses variaciones como "Mi experiencia" o "Estudios realizados".'
            ),
            'ejemplo': template,
        })

    for keyword in keywords_faltantes:
        recs.append({
            'tipo': 'keyword',
            'icono': '🔑',
            'titulo': f'Keyword faltante: "{keyword}"',
            'descripcion': (
                f'"{keyword}" es una keyword de alto impacto buscada frecuentemente '
                'en ofertas de trabajo tech.'
            ),
            'accion': (
                f'Mencioná "{keyword}" en tu sección de Habilidades Técnicas o '
                'integralo naturalmente en la descripción de tu experiencia laboral.'
            ),
            'ejemplo': (
                f'En Habilidades: "..., {keyword}, ..."\n'
                f'En Experiencia: "Desarrollé [funcionalidad] utilizando {keyword} en entorno de producción."'
            ),
        })

    return recs


def score_info(score: int) -> dict:
    if score >= 80:
        return {'label': 'Bueno', 'color': 'green', 'css': '#16a34a'}
    elif score >= 65:
        return {'label': 'Aceptable', 'color': 'yellow', 'css': '#d97706'}
    elif score >= 50:
        return {'label': 'Necesita mejora', 'color': 'orange', 'css': '#ea580c'}
    else:
        return {'label': 'Crítico', 'color': 'red', 'css': '#dc2626'}
