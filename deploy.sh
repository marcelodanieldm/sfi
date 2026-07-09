#!/bin/bash
# Deploy script para SFI en servidor de producción
# Uso: bash deploy.sh

set -e  # Detener en caso de error

echo "🚀 Iniciando deploy de SFI..."
echo ""

# Configurar variables
PROJECT_PATH="${PROJECT_PATH:-.}"
VENV_PATH="${VENV_PATH:-venv}"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📍 Ubicación del proyecto: $PROJECT_PATH${NC}"

# 1. Hacer pull de cambios
echo ""
echo -e "${YELLOW}📥 Haciendo pull de cambios...${NC}"
cd "$PROJECT_PATH"
git pull origin main

# 2. Activar entorno virtual
echo ""
echo -e "${YELLOW}🐍 Activando entorno virtual...${NC}"
source "$VENV_PATH/bin/activate"

# 3. Instalar dependencias
echo ""
echo -e "${YELLOW}📦 Instalando dependencias...${NC}"
pip install -r requirements.txt

# 4. Ejecutar migraciones
echo ""
echo -e "${YELLOW}🗄️  Ejecutando migraciones...${NC}"
python manage.py migrate --noinput

# 5. Recolectar archivos estáticos
echo ""
echo -e "${YELLOW}🎨 Recolectando archivos estáticos...${NC}"
python manage.py collectstatic --noinput

# 6. Cargar fixture de usuarios de prueba
echo ""
echo -e "${YELLOW}👥 Cargando fixture de usuarios con roles...${NC}"
python manage.py load_role_test_users --add-subscriptions

# 7. Compilar frontend (si aplica)
echo ""
echo -e "${YELLOW}🔨 Compilando frontend...${NC}"
cd frontend
npm install
npm run build
cd ..

# 8. Limpiar cache (opcional)
echo ""
echo -e "${YELLOW}🧹 Limpiando cache...${NC}"
python manage.py clear_cache 2>/dev/null || true

# 9. Restart del servicio
echo ""
echo -e "${YELLOW}🔄 Reiniciando servicio...${NC}"
echo -e "${YELLOW}Ejecutar uno de los siguientes comandos según tu configuración:${NC}"
echo ""
echo "  # Si usas Systemd:"
echo "  sudo systemctl restart sfi"
echo ""
echo "  # Si usas Supervisor:"
echo "  sudo supervisorctl restart sfi"
echo ""
echo "  # Si usas Gunicorn manual:"
echo "  pkill -f gunicorn; gunicorn skillsforit.wsgi --bind 0.0.0.0:8000 --workers 2 &"
echo ""

# Verificar que todo está bien
echo ""
echo -e "${GREEN}✅ Deploy completado!${NC}"
echo ""
echo "📊 Resumen:"
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
print(f'  Total de usuarios: {User.objects.count()}')
print(f'  Usuarios con rol: {User.objects.exclude(rol_it_preferido=\"\").count()}')
"
