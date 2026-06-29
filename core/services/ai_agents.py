"""
Agentes de IA para el flujo ATS Evaluator.

run_agent1: Parser & Profiler — analiza el CV y devuelve free_content.
run_agent2: Recommender      — genera las recomendaciones de paid_content.
"""

import hashlib
from core.services.ats_engine import analizar_cv, generar_recomendaciones


def run_agent1(cv_raw_text: str, jd_texto: str = '') -> dict:
    seed = hashlib.md5(cv_raw_text[:200].encode()).hexdigest()[:12]
    result = analizar_cv(seed, jd_texto)

    section_check = {}
    for s in result['secciones_presentes']:
        section_check[s] = True
    for s in result['secciones_faltantes']:
        section_check[s] = False

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


def run_agent2(cv_raw_text: str, job_description: str, free_content: dict) -> dict:
    parsing_issues   = free_content.get('parsing_issues', [])
    keyword_match    = free_content.get('keyword_match', {})
    section_check    = free_content.get('section_check', {})

    keywords_missing  = keyword_match.get('missing', [])
    sections_missing  = [s for s, present in section_check.items() if not present]

    actionable_fixes = generar_recomendaciones(keywords_missing, sections_missing, parsing_issues)

    tailored_summary = (
        'Tu CV tiene potencial pero necesita ajustes para superar los filtros ATS. '
        'Los puntos más críticos son los keywords faltantes y las secciones no detectadas. '
        'Aplicá las correcciones listadas abajo para aumentar tu score significativamente.'
    )

    return {
        'paid_content': {
            'tailored_summary':  tailored_summary,
            'actionable_fixes':  actionable_fixes,
        },
    }
