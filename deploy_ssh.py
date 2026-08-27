#!/usr/bin/env python3
"""
Script de deployment SSH para SFI
Ejecuta comandos de despliegue en el servidor remoto

Autenticación por clave SSH (sin contraseña en texto plano):
la clave privada debe estar en ~/.ssh/sfi_deploy y su pública
ya debe estar autorizada en el servidor (ver sfi_deploy_public_key.txt).
"""

import subprocess
import sys
import os

# Datos de conexión del servidor (sin credenciales sensibles)
HOST = "149.50.152.192"
PORT = 5333
USER = "root"
SSH_KEY = os.path.join(os.path.expanduser("~"), ".ssh", "sfi_deploy")

# Comandos a ejecutar
COMMANDS = [
    "cd /home/sfi",
    "echo '📦 Descargando cambios...'",
    "git pull origin main",
    "echo '✅ Git actualizado'",
    "",
    "echo '📥 Instalando dependencias Python...'",
    "pip install -r requirements.txt",
    "echo '✅ Dependencias Python instaladas'",
    "",
    "echo '🔄 Ejecutando migraciones...'",
    "python manage.py migrate",
    "echo '✅ Migraciones aplicadas'",
    "",
    "echo '🏗️  Compilando frontend...'",
    "cd frontend && npm install && npm run build && cd ..",
    "echo '✅ Frontend compilado'",
    "",
    "echo '📁 Recolectando archivos estáticos...'",
    "python manage.py collectstatic --noinput",
    "echo '✅ Archivos estáticos recolectados'",
    "",
    "echo '🚀 Deployment completado con éxito!'",
]

# Unir todos los comandos
full_command = " && ".join(COMMANDS)

# Crear comando SSH
try:
    print("🔐 Conectando al servidor...")
    print(f"   Host: {USER}@{HOST}:{PORT}")

    if not os.path.isfile(SSH_KEY):
        print(f"❌ No se encontró la clave privada en {SSH_KEY}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [
            "ssh",
            "-i", SSH_KEY,
            "-o", "StrictHostKeyChecking=no",
            "-p", str(PORT),
            f"{USER}@{HOST}",
            full_command,
        ],
        capture_output=False,
    )
    sys.exit(result.returncode)

except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)
