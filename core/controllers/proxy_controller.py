"""
Reverse proxy transparente para /campus/*

Cuando Django recibe GET /campus/algo, busca silenciosamente el contenido
en el servidor de Donweb (CAMPUS_ORIGIN) y lo devuelve al usuario.
El navegador nunca sabe que el contenido viene de otro servidor.

Configuración requerida en settings:
  CAMPUS_ORIGIN = 'https://skillsforit.online'  ← IP o dominio de Donweb
                                                    (diferente al dominio principal
                                                    una vez que Railway tome el control)

Ejemplos de uso:
  skillsforit.online/campus/        → Donweb /campus/
  skillsforit.online/campus/curso1  → Donweb /campus/curso1
  skillsforit.online/campus/img.png → Donweb /campus/img.png  (con query strings)
"""

import logging

import requests
from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger(__name__)

# Headers que no se reenvían al origen ni al cliente
_HOP_BY_HOP = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
    'content-encoding',  # requests descomprime solo; no reenviar
}


def campus_proxy(request, path=''):
    """
    GET|POST /campus/<path>

    Proxy transparente hacia CAMPUS_ORIGIN/campus/<path>.
    Reenvía query strings, cookies de sesión y el body en POST.
    Devuelve el contenido original con sus headers y status code.
    """
    origin = getattr(settings, 'CAMPUS_ORIGIN', '').rstrip('/')
    if not origin:
        logger.error('CAMPUS_ORIGIN no configurado en settings')
        return HttpResponse('Campus no disponible.', status=503)

    # Construir URL destino
    target_url = f'{origin}/campus/{path}'
    if request.GET:
        target_url += '?' + request.GET.urlencode()

    # Headers a reenviar (sin los hop-by-hop ni el Host original)
    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP | {'host'}
    }
    # Informar al origen quién hace la solicitud real
    forward_headers['X-Forwarded-For']   = request.META.get('REMOTE_ADDR', '')
    forward_headers['X-Forwarded-Host']  = request.get_host()
    forward_headers['X-Forwarded-Proto'] = 'https'

    try:
        upstream = requests.request(
            method  = request.method,
            url     = target_url,
            headers = forward_headers,
            data    = request.body if request.method in ('POST', 'PUT', 'PATCH') else None,
            cookies = request.COOKIES,
            timeout = 15,
            allow_redirects = True,
            stream  = False,
        )
    except requests.exceptions.ConnectionError:
        logger.error('Campus proxy: no se pudo conectar a %s', origin)
        return HttpResponse('Campus temporalmente no disponible.', status=502)
    except requests.exceptions.Timeout:
        logger.warning('Campus proxy: timeout en %s', target_url)
        return HttpResponse('El campus tardó demasiado en responder.', status=504)
    except Exception as exc:
        logger.exception('Campus proxy: error inesperado — %s', exc)
        return HttpResponse('Error interno del proxy.', status=500)

    # Construir respuesta Django con el contenido del origen
    response = HttpResponse(
        content      = upstream.content,
        status       = upstream.status_code,
        content_type = upstream.headers.get('Content-Type', 'text/html; charset=utf-8'),
    )

    # Reenviar headers relevantes del origen
    for header, value in upstream.headers.items():
        if header.lower() not in _HOP_BY_HOP | {'content-type', 'content-length'}:
            response[header] = value

    logger.info('Campus proxy: %s %s → %d', request.method, target_url, upstream.status_code)
    return response
