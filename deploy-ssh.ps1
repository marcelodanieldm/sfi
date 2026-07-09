# Script de Deploy por SSH en PowerShell
# Uso: .\deploy-ssh.ps1

param(
    [string]$Host = "149.50.152.192",
    [int]$Port = 5333,
    [string]$User = "root",
    [string]$Password = "9/gBTfa52)HuZk"
)

Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🚀 SFI DEPLOYMENT VIA SSH" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Script a ejecutar en el servidor
$deployScript = @"
cd /root && find . -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname
"@

# Comandos de deployment
$deployCommands = @"
echo '📦 [1/6] Descargando cambios...'
cd `$(find /root -name 'manage.py' -type f 2>/dev/null | head -1 | xargs dirname)
git pull origin main

echo '📥 [2/6] Instalando dependencias Python...'
pip install -r requirements.txt -q

echo '🔄 [3/6] Ejecutando migraciones...'
python manage.py migrate

echo '🏗️  [4/6] Compilando frontend...'
if [ -d 'frontend' ]; then
    cd frontend
    npm install -q
    npm run build
    cd ..
fi

echo '📁 [5/6] Recolectando archivos estáticos...'
python manage.py collectstatic --noinput -q

echo '✅ [6/6] Deployment completado!'
"@

try {
    Write-Host "🔐 Conectando a $User@$Host`:$Port..." -ForegroundColor Yellow
    Write-Host ""
    
    # Método 1: Intentar con SSH nativa (OpenSSH for Windows)
    if (Get-Command ssh.exe -ErrorAction SilentlyContinue) {
        Write-Host "✅ OpenSSH encontrado, usando ssh.exe" -ForegroundColor Green
        
        # Crear un archivo temporal con los comandos
        $tempScript = [System.IO.Path]::GetTempFileName()
        $deployCommands | Set-Content -Path $tempScript -Encoding UTF8
        
        Write-Host "Ejecutando deployment..." -ForegroundColor Yellow
        Write-Host ""
        
        # Ejecutar deployment
        ssh -o StrictHostKeyChecking=no -p $Port $User`@$Host @"
            $deployCommands
"@
        
        Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
        
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "✅ DEPLOYMENT COMPLETADO" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
        
    } else {
        Write-Host "❌ SSH no encontrado. Instalando opciones..." -ForegroundColor Red
        Write-Host ""
        Write-Host "Opción 1: Instalar OpenSSH for Windows" -ForegroundColor Yellow
        Write-Host "  Ejecutar en PowerShell (Admin):"
        Write-Host "  Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*' | Add-WindowsCapability -Online"
        Write-Host ""
        Write-Host "Opción 2: Instalar PuTTY (incluye plink.exe)" -ForegroundColor Yellow
        Write-Host "  choco install putty"
        Write-Host "  o descargar desde https://www.putty.org"
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📋 URL para verificar: https://sfi-production.up.railway.app/roleplay" -ForegroundColor Cyan
Write-Host ""
