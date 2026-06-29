import os

from django.contrib import admin
from django.urls import path, include, re_path
from revproxy.views import ProxyView

# IP o dominio de Donweb — configurable via env var en Railway
CAMPUS_UPSTREAM = os.environ.get('CAMPUS_ORIGIN', 'http://localhost').rstrip('/') + '/campus/'

urlpatterns = [
    path('sistema/', admin.site.urls),
    path('', include('core.urls', namespace='core')),

    # Puente transparente hacia Donweb:
    # skillsforit.online/campus/algo → busca en CAMPUS_ORIGIN/campus/algo
    re_path(
        r'^campus/(?P<path>.*)$',
        ProxyView.as_view(upstream=CAMPUS_UPSTREAM),
        name='campus_proxy',
    ),
]
