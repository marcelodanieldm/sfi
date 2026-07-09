# Manual de Deployment

## Estado Actual

✅ **Cambios pusheados a GitHub**: Commit `c4139a2`
- Backend: Escenarios dinámicos + endpoint de regeneración
- Frontend: Selector de roles simplificado + botón regenerar
- Migraciones: Schema actualizado

✅ **Despliegue Automático**: Railway.app ya detectó el push y está desplegando automáticamente via GitHub webhook

---

## Opción 1: Deployment Automático (Recomendado) ⭐

Railway.app ha sido configurado con webhook automático. Cuando pusheamos a GitHub, automáticamente:

1. ✅ Descarga cambios (`git pull`)
2. ✅ Instala dependencias (`pip install -r requirements.txt`, `npm install`)
3. ✅ Ejecuta migraciones (`python manage.py migrate`)
4. ✅ Compila frontend (`npm run build`)
5. ✅ Reinicia servidor

**Estado del deployment**: Railway detecta pushes cada ~30 segundos

**URL del servidor**: https://sfi-production.up.railway.app/ (Railway proporciona URL automática)

---

## Opción 2: Deployment Manual al Servidor

### ⚠️ Nota sobre SSH
La autenticación SSH por contraseña puede tener limitaciones en algunos sistemas. Si SSH no funciona con contraseña, hay alternativas:
1. **Usar SSH key** (recomendado): Configura una SSH key en el servidor
2. **Usar Railway CLI** (más fácil): Instala Railway CLI y usa `railway up`
3. **Acceso a servidor**: Usa console web del proveedor (DigitalOcean, Linode, etc.) para ejecutar comandos

### Requisitos
- SSH access a `root@149.50.152.192` con puerto 5333
- O acceso a console web del servidor
- O Railway CLI instalado

### Pasos (Opción A: SSH)

#### 1. Conectarse al servidor
```bash
ssh -p 5333 root@149.50.152.192

# O si tienes SSH key:
ssh -i ~/.ssh/id_rsa -p 5333 root@149.50.152.192
```

#### 2. Navegar al directorio del proyecto
El proyecto puede estar en diferentes ubicaciones. Ejecutar:
```bash
# Buscar el proyecto
find / -name "manage.py" -type f 2>/dev/null | head -1

# O si ya sabes la ruta (ejemplo):
cd /var/www/sfi
# o
cd /home/sfi
# o
cd /opt/sfi
```

#### 3. Descargar cambios
```bash
git pull origin main
```

#### 4. Ejecutar script de despliegue
```bash
bash deploy.sh
```

### Pasos (Opción B: Railway CLI)

Si tienes Railway CLI instalado:
```bash
# Instalar Railway CLI (si no lo tienes)
npm install -g @railway/cli

# Ingresar con GitHub
railway login

# Ver logs
railway logs

# Redeploy
railway up
```

### Pasos (Opción C: Console Web del Servidor)

Si accedes a través de la console web (DigitalOcean, Linode, Hetzner, etc.):
1. Abre la console/terminal desde el panel del proveedor
2. Copia y pega los comandos de despliegue:
```bash
cd /var/www/sfi  # o la ruta correcta
git pull origin main
bash deploy.sh
```

El script ejecutará:
```bash
#!/bin/bash
set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Deployment complete! ✅"
```

#### 5. Verificar despliegue
```bash
# Ver status del servicio
sudo systemctl status sfi

# Ver logs
tail -f /var/log/sfi/app.log

# Probar endpoint
curl http://localhost:8000/api/v1/roleplay/roles/
```

### Troubleshooting SSH

**Error: "Permission denied, please try again"**
- La contraseña SSH es incorrecta o no funciona por SSH interactivo
- Solución: Usa Railway CLI, console web, o SSH key en lugar de contraseña

**Error: "Could not resolve hostname"**
- Problema de conectividad de red
- Verifica: `ping 149.50.152.192`
- Verifica que puerto 5333 no está bloqueado: `telnet 149.50.152.192 5333`

**Error: "Connection refused"**
- El servidor SSH no está escuchando
- Contacta con tu proveedor de hosting

### Troubleshooting Deployment

**Error: "git pull" rechazado**
```bash
git status
git stash  # si hay cambios locales
git pull
```

**Error: "npm install" falla**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Error: "pip install" falla**
```bash
# Asegurarse que venv está activado
source venv/bin/activate  # Linux/Mac
# o en Windows:
venv\Scripts\activate

# Intentar de nuevo
pip install -r requirements.txt
```

**Error: Migraciones rechazadas**
```bash
# Ver migraciones aplicadas
python manage.py showmigrations core

# Si hay problemas, rollback:
python manage.py migrate core 0010
python manage.py migrate core 0011
```

**Error: "manage.py: No such file or directory"**
- Estás en el directorio equivocado
- Ejecutar: `find / -name "manage.py" -type f 2>/dev/null`
- Ir al directorio encontrado: `cd /path/to/project`

**Error: Variable de entorno OPENAI_API_KEY no set**
```bash
export OPENAI_API_KEY="sk-..."
# O agregar a ~/.bashrc para persistencia
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
source ~/.bashrc
```

---

## Opción 3: Verificar Estado en Railway

### Dashboard Railway
1. Ir a https://railway.app
2. Ingresar con GitHub (usa marcelodanieldm/sfi)
3. Ver "Latest Deployment" 
4. Verificar logs en "Logs" tab
5. Copiar URL pública del deployment

### Comandos Railway CLI
```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Ingresar
railway login

# Ver logs
railway logs

# Redeploy si es necesario
railway up
```

---

## Verificación Post-Deployment

### 1. Endpoints activos
```bash
# Listar roles disponibles
curl -H "X-CSRFToken: $(curl -s http://localhost:8000 | grep -o 'csrftoken":[^}]*' | cut -d'"' -f3)" http://localhost:8000/api/v1/roleplay/roles/

# Crear sesión con escenario dinámico
curl -X POST http://localhost:8000/api/v1/roleplay/sessions/start/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{"rol_it_sesion": "backend"}'
```

### 2. Base de datos
```bash
python manage.py dbshell

# Verificar nuevas columnas en RoleplaySession
.schema core_roleplaysession

# Ver sesiones con escenarios dinámicos
SELECT id, rol_it_sesion, scenario_generated, regenerate_count 
FROM core_roleplaysession 
WHERE scenario_generated IS NOT NULL 
LIMIT 5;
```

### 3. Frontend
- Navegar a `https://sfi-production.up.railway.app/roleplay`
- Ver modal de selección de roles
- Seleccionar un rol
- Verificar que se genera escenario y carga chat

### 4. Logs
```bash
# Backend logs
tail -f /var/log/sfi/app.log | grep roleplay

# Frontend build (en Railway)
railway logs | grep "npm run build"
```

---

## Rollback en Caso de Error

### Git rollback
```bash
# Ver commits recientes
git log --oneline -5

# Revertir a commit anterior
git revert c4139a2  # Crear un nuevo commit de reversa

# O hard reset (DANGEROUS - usa solo en desarrollo)
git reset --hard 36bd2b0
git push -f origin main
```

### Database rollback
```bash
python manage.py migrate core 0010  # Revertir a migración anterior
```

---

## Monitoreo Continuo

### Recomendaciones
1. Monitorear logs después del deployment (primeras 2 horas)
2. Probar endpoints críticos con usuarios de test
3. Verificar errores de OpenAI API en logs
4. Monitorear uso de API key de OpenAI en console.openai.com

### Métricas a Monitorear
- Latencia de generación de escenarios (debe ser < 5 segundos)
- Errores de OpenAI API
- Tasa de uso de tokens de OpenAI
- Sesiones completadas vs abandonadas

---

## Resumen Rápido

**Para deployment automático (recomendado):**
1. ✅ Ya está hecho, Railway lo hace automáticamente
2. Esperar ~30 segundos a que Railway detecte el push
3. Verificar en https://railway.app dashboard

**Para deployment manual:**
```bash
ssh -p 5333 root@149.50.152.192
cd /home/sfi && git pull && bash deploy.sh
```

**Verificación:**
```bash
curl https://sfi-production.up.railway.app/api/v1/roleplay/roles/
```

---

## Contacto / Soporte

Si hay problemas durante el deployment:
1. Revisar logs en Railway dashboard
2. Verificar migraciones: `python manage.py showmigrations`
3. Verificar variables de entorno (especialmente `OPENAI_API_KEY`)
4. Probar localmente en desarrollo: `python manage.py runserver`
