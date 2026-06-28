"""
Entry point para Passenger WSGI (Donweb / cPanel).
Colocar en el directorio raíz de la app configurado en cPanel.
"""
import os
import sys

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skillsforit.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
