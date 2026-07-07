"""
Agentes de IA para el flujo ATS Evaluator.

run_agent1  — Analiza el CV con OpenAI: score, keywords, secciones, problemas de formato.
run_agent2  — Genera el plan de acción con recomendaciones accionables via OpenAI.

Si OPENAI_API_KEY no está configurada o la llamada falla, ambos caen al motor
determinístico de ats_engine para que el flujo nunca se rompa.
"""

from __future__ import annotations

import json
import logging

import openai
from django.conf import settings

from core.services.ats_engine import analizar_cv, generar_recomendaciones

logger = logging.getLogger(__name__)

_SECCIONES = [
    'Experiencia Laboral',
    'Educación',
    'Habilidades Técnicas',
    'Proyectos',
    'Certificaciones',
    'Perfil Profesional',
]

# ────────────────────────────────────────────────────────────────────────────
#  Prompts
# ────────────────────────────────────────────────────────────────────────────

_SYSTEM_AGENT1 = """\
Eres un experto en sistemas ATS (Applicant Tracking Systems) especializado en CVs del sector IT.

Analizá el texto extraído de un CV en PDF y evaluá su compatibilidad ATS.

Devolvé SOLO un JSON válido con exactamente esta estructura, sin texto adicional fuera del JSON:
{
  "ats_score": <entero 0-100>,
  "parsing_issues": [<strings con problemas de formato, máximo 4>],
  "keywords_found": [<strings: keywords tecnológicas presentes en el CV>],
  "keywords_missing": [<strings: keywords tecnológicas importantes ausentes del CV, máximo 12>],
  "section_check": {
    "Experiencia Laboral": <true o false>,
    "Educación": <true o false>,
    "Habilidades Técnicas": <true o false>,
    "Proyectos": <true o false>,
    "Certificaciones": <true o false>,
    "Perfil Profesional": <true o false>
  }
}

Criterios de scoring:
  80–100 → Excelente compatibilidad ATS, pocas mejoras necesarias.
  65–79  → Aceptable, con mejoras moderadas posibles.
  50–64  → Necesita trabajo; keywords o secciones importantes ausentes.
  0–49   → Crítico; problemas de formato o contenido que bloquean el parsing.

Para parsing_issues detectá: tablas, diseño en 2+ columnas, foto o imagen embebida,
fuentes decorativas o íconos en lugar de texto, barras de progreso gráficas,
encabezados con información que el ATS no puede parsear, caracteres especiales.

Para keywords cubrí: lenguajes de programación, frameworks, bases de datos, herramientas
DevOps, cloud, metodologías ágiles, testing, y cualquier tecnología IT relevante.

Si el texto del CV está casi vacío o ilegible, asigná score bajo (20–40) e incluí
"El PDF parece basado en imágenes o estar protegido — el texto no fue extraíble correctamente"
en parsing_issues.\
"""

_SYSTEM_AGENT2 = """\
Eres un experto en optimización de CVs para sistemas ATS y el mercado IT latinoamericano.

A partir del análisis ATS ya realizado, generá un plan de acción concreto y accionable.

Devolvé SOLO un JSON válido con exactamente esta estructura, sin texto adicional fuera del JSON:
{
  "tailored_summary": "<resumen de 2-3 oraciones sobre el estado del CV y qué necesita mejorar, tono directo y profesional, en español rioplatense>",
  "actionable_fixes": [
    {
      "tipo": "<exactamente uno de: 'formato', 'seccion', 'keyword'>",
      "icono": "<emoji relevante>",
      "titulo": "<título corto del problema, máximo 60 caracteres>",
      "descripcion": "<qué problema tiene y por qué afecta el score ATS, 1-2 oraciones>",
      "accion": "<instrucción concreta de qué hacer, 1-3 oraciones>",
      "ejemplo": "<texto de ejemplo listo para copiar y pegar en el CV>"
    }
  ]
}

Generá entre 4 y 10 fixes ordenados por impacto descendente:
primero problemas de formato (bloquean todo el parsing), luego secciones faltantes,
luego keywords ausentes.

Sé muy específico con los ejemplos — el usuario debe poder copiarlos y pegarlos
directamente en su CV sin necesidad de adaptarlos.

Escribí todo en español rioplatense (Argentina).\
"""

# ────────────────────────────────────────────────────────────────────────────
#  Agentes públicos
# ────────────────────────────────────────────────────────────────────────────

def run_agent1(cv_raw_text: str, jd_texto: str = '') -> dict:
    """
    Analiza el CV y devuelve score + free_content.
    Usa OpenAI si está configurado; cae al motor determinístico si no.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        logger.warning('OPENAI_API_KEY no configurada — usando motor determinístico para Agent 1')
        return _agent1_fallback(cv_raw_text, jd_texto)

    user_msg = f"Texto del CV:\n\n{cv_raw_text[:6000]}"
    if jd_texto.strip():
        user_msg += f"\n\n---\nDescripción del trabajo (oferta):\n{jd_texto[:2000]}"

    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model='gpt-4o-mini',
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': _SYSTEM_AGENT1},
                {'role': 'user',   'content': user_msg},
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        data = json.loads(resp.choices[0].message.content)
        return _agent1_from_json(data)

    except Exception as exc:
        logger.error('Agent 1 OpenAI error (%s) — usando fallback', exc)
        return _agent1_fallback(cv_raw_text, jd_texto)


def run_agent2(cv_raw_text: str, job_description: str, free_content: dict) -> dict:
    """
    Genera recomendaciones accionables a partir del análisis previo.
    Usa OpenAI si está configurado; cae al motor determinístico si no.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        logger.warning('OPENAI_API_KEY no configurada — usando motor determinístico para Agent 2')
        return _agent2_fallback(free_content)

    keyword_match    = free_content.get('keyword_match', {})
    section_check    = free_content.get('section_check', {})
    parsing_issues   = free_content.get('parsing_issues', [])
    keywords_found   = keyword_match.get('found', [])
    keywords_missing = keyword_match.get('missing', [])
    sections_missing = [s for s, ok in section_check.items() if not ok]

    user_msg = (
        f"Texto del CV (primeras 4000 chars):\n{cv_raw_text[:4000]}\n\n"
        f"Problemas de formato detectados: {', '.join(parsing_issues) or 'ninguno'}\n"
        f"Keywords presentes en el CV: {', '.join(keywords_found) or 'ninguna'}\n"
        f"Keywords importantes ausentes: {', '.join(keywords_missing) or 'ninguna'}\n"
        f"Secciones faltantes: {', '.join(sections_missing) or 'ninguna'}"
    )
    if job_description:
        user_msg += f"\n\nDescripción del trabajo:\n{job_description[:1500]}"

    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model='gpt-4o-mini',
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': _SYSTEM_AGENT2},
                {'role': 'user',   'content': user_msg},
            ],
            temperature=0.3,
            max_tokens=2500,
        )
        data = json.loads(resp.choices[0].message.content)
        return {
            'paid_content': {
                'tailored_summary': data.get('tailored_summary', ''),
                'actionable_fixes': _validate_fixes(data.get('actionable_fixes', [])),
            }
        }

    except Exception as exc:
        logger.error('Agent 2 OpenAI error (%s) — usando fallback', exc)
        return _agent2_fallback(free_content)


# ────────────────────────────────────────────────────────────────────────────
#  Helpers internos
# ────────────────────────────────────────────────────────────────────────────

def _agent1_from_json(data: dict) -> dict:
    section_check_raw = data.get('section_check', {})
    section_check = {s: bool(section_check_raw.get(s, False)) for s in _SECCIONES}

    return {
        'ats_score': max(0, min(100, int(data.get('ats_score', 50)))),
        'free_content': {
            'parsing_issues': list(data.get('parsing_issues', [])),
            'keyword_match': {
                'found':   list(data.get('keywords_found', [])),
                'missing': list(data.get('keywords_missing', [])),
            },
            'section_check': section_check,
        },
    }


def _validate_fixes(fixes: list) -> list:
    valid_tipos = {'formato', 'seccion', 'keyword'}
    result = []
    for f in fixes:
        if not isinstance(f, dict):
            continue
        tipo = f.get('tipo', 'keyword')
        if tipo not in valid_tipos:
            tipo = 'keyword'
        result.append({
            'tipo':        tipo,
            'icono':       f.get('icono', '🔧'),
            'titulo':      str(f.get('titulo', ''))[:80],
            'descripcion': str(f.get('descripcion', '')),
            'accion':      str(f.get('accion', '')),
            'ejemplo':     str(f.get('ejemplo', '')),
        })
    return result


def _agent1_fallback(cv_raw_text: str, jd_texto: str) -> dict:
    import hashlib
    seed = hashlib.md5(cv_raw_text[:200].encode()).hexdigest()[:12]
    result = analizar_cv(seed, jd_texto)

    section_check = {s: True  for s in result['secciones_presentes']}
    section_check.update({s: False for s in result['secciones_faltantes']})

    return {
        'ats_score': result['score_ats'],
        'free_content': {
            'parsing_issues': result['problemas_formato'],
            'keyword_match': {
                'found':   result['keywords_encontradas'],
                'missing': result['keywords_faltantes'],
            },
            'section_check': section_check,
        },
    }


def _agent2_fallback(free_content: dict) -> dict:
    keyword_match    = free_content.get('keyword_match', {})
    section_check    = free_content.get('section_check', {})
    parsing_issues   = free_content.get('parsing_issues', [])
    keywords_missing = keyword_match.get('missing', [])
    sections_missing = [s for s, ok in section_check.items() if not ok]

    actionable_fixes = generar_recomendaciones(keywords_missing, sections_missing, parsing_issues)
    return {
        'paid_content': {
            'tailored_summary': (
                'Tu CV tiene potencial pero necesita ajustes para superar los filtros ATS. '
                'Aplicá las correcciones listadas para aumentar tu score significativamente.'
            ),
            'actionable_fixes': actionable_fixes,
        },
    }
