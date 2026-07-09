#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skillsforit.settings')
django.setup()

from core.models import RoleplaySession

# Obtener la sesión más reciente
session = RoleplaySession.objects.order_by('-created_at').first()
if session:
    print(f"Session ID: {session.id}")
    print(f"Role: '{session.rol_it_sesion}'")
    print(f"Status: {session.status}")
    print(f"User: {session.user}")
    print(f"Scenario: {session.scenario}")
    print(f"Scenario Generated: {session.scenario_generated}")
else:
    print("No sessions found")
