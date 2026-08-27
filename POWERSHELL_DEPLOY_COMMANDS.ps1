# COMANDOS DE DEPLOYMENT PARA POWERSHELL
# Copiar y ejecutar directamente en PowerShell

# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 1: Si tienes OpenSSH instalado (Windows 10/11+)
# ════════════════════════════════════════════════════════════════════════════

ssh -o StrictHostKeyChecking=no -p 5333 root@149.50.152.192 "cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname | xargs -I {} bash -c 'cd {} && git pull origin main && pip install -r requirements.txt -q && python manage.py migrate && cd frontend && npm install -q && npm run build && cd .. && python manage.py collectstatic --noinput -q && echo Deployment completado'"


# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 2: Con clave SSH (recomendado, sin contraseña en texto plano)
# La clave privada debe estar en ~/.ssh/sfi_deploy (ya autorizada en el servidor)
# ════════════════════════════════════════════════════════════════════════════

ssh -i "$HOME\.ssh\sfi_deploy" -o StrictHostKeyChecking=no -p 5333 root@149.50.152.192 "cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname | xargs -I {} bash -c 'cd {} && git pull origin main && pip install -r requirements.txt -q && python manage.py migrate && cd frontend && npm install -q && npm run build && cd .. && python manage.py collectstatic --noinput -q && echo ✅ Deployment completado'"


# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 3: Función PowerShell reutilizable (clave SSH)
# ════════════════════════════════════════════════════════════════════════════

# Guardar la función en tu perfil de PowerShell ($PROFILE)
function Deploy-SFI {
    param(
        [string]$Host = "149.50.152.192",
        [int]$Port = 5333,
        [string]$User = "root",
        [string]$KeyPath = "$HOME\.ssh\sfi_deploy"
    )

    if (-not (Test-Path $KeyPath)) {
        Write-Host "❌ No se encontró la clave privada en $KeyPath" -ForegroundColor Red
        return
    }

    $deployCmd = "cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname | xargs -I {} bash -c 'cd {} && git pull origin main && pip install -r requirements.txt -q && python manage.py migrate && cd frontend && npm install -q && npm run build && cd .. && python manage.py collectstatic --noinput -q && echo ✅ Deployment completado'"

    ssh -i $KeyPath -o StrictHostKeyChecking=no -p $Port $User@$Host $deployCmd
}

# Uso:
# Deploy-SFI


# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 4: Con visualización step-by-step
# ════════════════════════════════════════════════════════════════════════════

function Deploy-SFI-Verbose {
    param(
        [string]$Host = "149.50.152.192",
        [int]$Port = 5333,
        [string]$User = "root",
        [string]$KeyPath = "$HOME\.ssh\sfi_deploy"
    )

    Write-Host "🚀 Iniciando deployment de SFI..." -ForegroundColor Cyan
    Write-Host ""

    if (-not (Test-Path $KeyPath)) {
        Write-Host "❌ No se encontró la clave privada en $KeyPath" -ForegroundColor Red
        return
    }

    $steps = @(
        "echo '📦 [1/6] Descargando cambios'; git pull origin main",
        "echo '📥 [2/6] Instalando dependencias'; pip install -r requirements.txt -q",
        "echo '🔄 [3/6] Ejecutando migraciones'; python manage.py migrate",
        "echo '🏗️  [4/6] Compilando frontend'; cd frontend && npm install -q && npm run build && cd ..",
        "echo '📁 [5/6] Recolectando estáticos'; python manage.py collectstatic --noinput -q",
        "echo '✅ [6/6] Deployment completado!'"
    )

    $findProject = "cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname"
    $fullCommand = "$findProject && " + ($steps -join " && ")

    ssh -i $KeyPath -o StrictHostKeyChecking=no -p $Port $User@$Host $fullCommand
}

# Uso:
# Deploy-SFI-Verbose
