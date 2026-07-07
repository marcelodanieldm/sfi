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
El CV puede estar en español o en inglés — detectá el idioma y respondé los textos en ese mismo idioma
(los campos parsing_issues deben estar en el idioma del CV).

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
un mensaje indicando que el PDF parece estar basado en imágenes o estar protegido, en el idioma detectado.\
"""

_SYSTEM_AGENT2 = """\
Eres un experto senior en optimización de CVs para sistemas ATS y el mercado IT latinoamericano.

A partir del texto del CV y el análisis ATS base, generá un análisis completo y premium.

Devolvé SOLO un JSON válido con exactamente esta estructura, sin texto adicional fuera del JSON:
{
  "tailored_summary": "<resumen ejecutivo de 2-3 oraciones sobre el estado del CV, tono directo y profesional, en español rioplatense>",
  "section_analysis": [
    {
      "seccion": "<nombre exacto de la sección, ej: Experiencia Laboral>",
      "evaluacion": "<exactamente uno de: excelente, aceptable, necesita_mejora, critico, ausente>",
      "problemas": ["<problema específico y concreto detectado en la sección>"],
      "sugerencia_estructura": "<1-2 oraciones explicando cómo debería estructurarse esta sección>",
      "ejemplo_redaccion": ["<bullet o fragmento completo y real listo para copiar al CV>"]
    }
  ],
  "keyword_integration": [
    {
      "keyword": "<keyword faltante>",
      "seccion": "<sección donde integrarlo, ej: Habilidades Técnicas>",
      "ejemplo": "<oración completa y natural lista para copiar al CV>"
    }
  ],
  "actionable_fixes": [
    {
      "tipo": "<exactamente uno de: formato, seccion, keyword>",
      "icono": "<emoji relevante>",
      "titulo": "<título corto del problema, máximo 60 caracteres>",
      "descripcion": "<qué problema tiene y por qué afecta el score ATS, 1-2 oraciones>",
      "accion": "<instrucción concreta de qué hacer, 1-3 oraciones>",
      "ejemplo": "<texto listo para copiar al CV>"
    }
  ]
}

Para section_analysis:
- Analizá SOLO las secciones relevantes del CV (Experiencia Laboral, Habilidades Técnicas, Educación, Proyectos, Certificaciones, Perfil Profesional).
- Para Experiencia: evaluá si los bullets están cuantificados con impacto medible (números, porcentajes, usuarios impactados).
- Para Habilidades: evaluá si las keywords de la industria están listadas correctamente en formato legible para ATS.
- Para secciones ausentes marcalas como 'ausente' con sugerencias de cómo agregarlas.
- Proporcioná siempre 2-3 bullets ejemplo reales y específicos para el contexto del candidato.
- Incluí todas las secciones (presentes y faltantes críticas), mínimo 3 secciones.

Para keyword_integration:
- Elegí las 4-6 keywords más críticas faltantes (priorizar las del job description si existe).
- Dá oraciones naturales, no forzadas, que un humano podría escribir en su CV.

Para actionable_fixes:
- Generá entre 5 y 8 fixes ordenados por impacto descendente.
- Primero formato (bloquean parsing), luego secciones faltantes, luego keywords.

IDIOMA: Detectá el idioma del CV. Si el CV está en inglés, escribí TODOS los textos en inglés.
Si el CV está en español, escribí en español rioplatense (Argentina).
Aplicá esto a todos los campos de texto: tailored_summary, section_analysis, keyword_integration y actionable_fixes.\
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
    Genera el análisis premium: sección por sección, integración de keywords y fixes.
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
    sections_present = [s for s, ok in section_check.items() if ok]
    sections_missing = [s for s, ok in section_check.items() if not ok]

    user_msg = (
        f"Texto del CV (primeras 5000 chars):\n{cv_raw_text[:5000]}\n\n"
        f"=== Resultado del análisis ATS ===\n"
        f"Problemas de formato: {', '.join(parsing_issues) or 'ninguno'}\n"
        f"Secciones presentes: {', '.join(sections_present) or 'ninguna'}\n"
        f"Secciones faltantes: {', '.join(sections_missing) or 'ninguna'}\n"
        f"Keywords encontradas en el CV: {', '.join(keywords_found) or 'ninguna'}\n"
        f"Keywords importantes ausentes: {', '.join(keywords_missing) or 'ninguna'}"
    )
    if job_description:
        user_msg += f"\n\n=== Descripción del trabajo (JD) ===\n{job_description[:2000]}"

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
            max_tokens=3500,
        )
        data = json.loads(resp.choices[0].message.content)
        return {
            'paid_content': {
                'tailored_summary':    data.get('tailored_summary', ''),
                'section_analysis':    _validate_section_analysis(data.get('section_analysis', [])),
                'keyword_integration': _validate_keyword_integration(data.get('keyword_integration', [])),
                'actionable_fixes':    _validate_fixes(data.get('actionable_fixes', [])),
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


def _validate_section_analysis(sections: list) -> list:
    valid_evals = {'excelente', 'aceptable', 'necesita_mejora', 'critico', 'ausente'}
    result = []
    for s in sections:
        if not isinstance(s, dict):
            continue
        evaluacion = s.get('evaluacion', 'aceptable')
        if evaluacion not in valid_evals:
            evaluacion = 'aceptable'
        result.append({
            'seccion':             str(s.get('seccion', ''))[:80],
            'evaluacion':          evaluacion,
            'problemas':           [str(p) for p in s.get('problemas', []) if p][:5],
            'sugerencia_estructura': str(s.get('sugerencia_estructura', '')),
            'ejemplo_redaccion':   [str(e) for e in s.get('ejemplo_redaccion', []) if e][:5],
        })
    return result


def _validate_keyword_integration(integrations: list) -> list:
    result = []
    for item in integrations:
        if not isinstance(item, dict):
            continue
        result.append({
            'keyword': str(item.get('keyword', ''))[:60],
            'seccion': str(item.get('seccion', ''))[:80],
            'ejemplo': str(item.get('ejemplo', '')),
        })
    return result[:8]


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

    section_analysis = []
    for s, present in section_check.items():
        section_analysis.append({
            'seccion':               s,
            'evaluacion':            'aceptable' if present else 'ausente',
            'problemas':             [] if present else [f'La sección "{s}" no fue detectada por el ATS.'],
            'sugerencia_estructura': '',
            'ejemplo_redaccion':     [],
        })

    keyword_integration = [
        {
            'keyword': kw,
            'seccion': 'Habilidades Técnicas',
            'ejemplo': f'En Habilidades Técnicas: "..., {kw}, ..." — o en Experiencia: "Desarrollé [feature] utilizando {kw}."',
        }
        for kw in keywords_missing[:5]
    ]

    return {
        'paid_content': {
            'tailored_summary': (
                'Tu CV tiene potencial pero necesita ajustes para superar los filtros ATS. '
                'Aplicá las correcciones listadas para aumentar tu score significativamente.'
            ),
            'section_analysis':    section_analysis,
            'keyword_integration': keyword_integration,
            'actionable_fixes':    actionable_fixes,
        },
    }
