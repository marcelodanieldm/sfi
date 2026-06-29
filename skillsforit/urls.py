import os

from django.contrib import admin
from django.urls import path, include, re_path
from revproxy.views import ProxyView

# TODO: Cambia el valor por defecto 'http://REMPLAZAR_CON_IP_DONWEB' por la IP
#       real de tu servidor Donweb, o bien setea la variable de entorno
#       CAMPUS_ORIGIN en Railway (recomendado para producción).
#       Ejemplo: CAMPUS_ORIGIN=http://181.xxx.xxx.xxx
CAMPUS_UPSTREAM = os.environ.get('CAMPUS_ORIGIN', 'http://200.58.112.252').rstrip('/') + '/campus/'


class CampusProxyView(ProxyView):
    """
    Extiende ProxyView para reenviar las cabeceras de protocolo al servidor
    de Moodle, evitando que genere URLs HTTP cuando el visitante usa HTTPS.
    """
    add_remote_user = False

    def get_request_headers(self):
        headers = super().get_request_headers()
        # Reenvía el protocolo original al upstream para que Moodle construya
        # sus URLs de CSS/JS con el esquema correcto (http vs https).
        proto = self.request.META.get('HTTP_X_FORWARDED_PROTO') or (
            'https' if self.request.is_secure() else 'http'
        )
        headers['X-Forwarded-Proto'] = proto
        headers['X-Forwarded-Host'] = self.request.get_host()
        return headers


urlpatterns = [
    path('sistema/', admin.site.urls),
    path('', include('core.urls', namespace='core')),

    # Puente transparente hacia Donweb:
    # skillsforit.online/campus/algo → http://<IP_DONWEB>/campus/algo
    re_path(
        r'^campus/(?P<path>.*)$',
        CampusProxyView.as_view(upstream=CAMPUS_UPSTREAM),
        name='campus_proxy',
    ),
]
