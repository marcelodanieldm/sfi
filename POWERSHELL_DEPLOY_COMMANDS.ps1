# COMANDOS DE DEPLOYMENT PARA POWERSHELL
# Copiar y ejecutar directamente en PowerShell

# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 1: Si tienes OpenSSH instalado (Windows 10/11+)
# ════════════════════════════════════════════════════════════════════════════

ssh -o StrictHostKeyChecking=no -p 5333 root@149.50.152.192 "cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname | xargs -I {} bash -c 'cd {} && git pull origin main && pip install -r requirements.txt -q && python manage.py migrate && cd frontend && npm install -q && npm run build && cd .. && python manage.py collectstatic --noinput -q && echo Deployment completado'"


# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 2: Si tienes PuTTY instalado (con plink.exe)
# ════════════════════════════════════════════════════════════════════════════

plink.exe -pw "9/gBTfa52)HuZk" -P 5333 root@149.50.152.192 "cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname | xargs -I {} bash -c 'cd {} && git pull origin main && pip install -r requirements.txt -q && python manage.py migrate && cd frontend && npm install -q && npm run build && cd .. && python manage.py collectstatic --noinput -q && echo ✅ Deployment completado'"


# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 3: Script PowerShell interactivo (pide datos manualmente)
# ════════════════════════════════════════════════════════════════════════════

# Guardar la función en tu perfil de PowerShell ($PROFILE)
function Deploy-SFI {
    param(
        [string]$Host = "149.50.152.192",
        [int]$Port = 5333,
        [string]$User = "root"
    )
    
    $password = Read-Host "Contraseña SSH" -AsSecureString
    $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($password))
    
    # Ejecutar con plink (más confiable en Windows)
    $deployCmd = "cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname | xargs -I {} bash -c 'cd {} && git pull origin main && pip install -r requirements.txt -q && python manage.py migrate && cd frontend && npm install -q && npm run build && cd .. && python manage.py collectstatic --noinput -q && echo ✅ Deployment completado'"
    
    plink.exe -pw $plainPassword -P $Port $User@$Host $deployCmd
}

# Uso:
# Deploy-SFI


# ════════════════════════════════════════════════════════════════════════════
# OPCIÓN 4: Con visualización step-by-step
# ════════════════════════════════════════════════════════════════════════════

function Deploy-SFI-Verbose {
    Write-Host "🚀 Iniciando deployment de SFI..." -ForegroundColor Cyan
    Write-Host ""
    
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
    
    plink.exe -pw "9/gBTfa52)HuZk" -P 5333 root@149.50.152.192 $fullCommand
}

# Uso:
# Deploy-SFI-Verbose
