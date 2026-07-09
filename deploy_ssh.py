#!/usr/bin/env python3
"""
Script de deployment SSH para SFI
Ejecuta comandos de despliegue en el servidor remoto
"""

import subprocess
import sys
import os

# Credenciales del servidor
HOST = "149.50.152.192"
PORT = 5333
USER = "root"
PASSWORD = "9/gBTfa52)HuZk"

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
    # Intentar con expect (más confiable en Linux, pero Windows PowerShell puede tener issues)
    # Fallback a simple SSH command
    print("🔐 Conectando al servidor...")
    print(f"   Host: {USER}@{HOST}:{PORT}")
    
    # Usar script de expect si está disponible, sino usar método alternativo
    import platform
    
    if platform.system() == "Windows":
        # En Windows, usar un wrapper que maneje la contraseña
        print("ℹ️  Usando método PowerShell...")
        
        # Crear un script PowerShell temporal
        ps_script = """
        param([string]$password, [string]$command)
        
        $securePassword = ConvertTo-SecureString $password -AsPlainText -Force
        $credential = New-Object System.Management.Automation.PSCredential("root", $securePassword)
        
        # Usar OpenSSH si está disponible
        ssh -o StrictHostKeyChecking=no -p 5333 root@149.50.152.192 $command
        """
        
        # Guardar script temporal
        ps_file = "temp_deploy_script.ps1"
        with open(ps_file, 'w') as f:
            f.write(ps_script)
        
        # Ejecutar
        result = subprocess.run(
            ["powershell", "-File", ps_file, "-password", PASSWORD, "-command", full_command],
            capture_output=False
        )
        
        # Limpiar
        os.remove(ps_file)
        
    else:
        # En Linux/Mac, intentar con expect
        print("ℹ️  Usando método expect...")
        
        expect_script = f"""
        #!/usr/bin/expect
        spawn ssh -o StrictHostKeyChecking=no -p {PORT} {USER}@{HOST}
        expect "password:"
        send "{PASSWORD}\\r"
        expect "$"
        send "{full_command}\\r"
        expect "$"
        send "exit\\r"
        expect eof
        """
        
        # Ejecutar con expect
        result = subprocess.run(
            ["expect", "-c", expect_script],
            capture_output=False
        )

except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)
