# Implementación de Escenarios Dinámicos de Roleplay

## Descripción General

Este documento detalla la implementación de **generación dinámica de escenarios de roleplay** usando OpenAI, reemplazando el sistema anterior de escenarios predefinidos en base de datos.

**Beneficio principal**: Los escenarios se generan al azar en tiempo real según el rol IT del usuario, sin necesidad de almacenamiento en BD (cost-optimized).

---

## Cambios en el Backend

### 1. **core/models.py** - Extensión del modelo `RoleplaySession`

Nuevos campos:
- `scenario_generated` (JSONField): Almacena el escenario generado por OpenAI (estructura: title, context, user_role, bot_role, initial_bot_message, max_turns)
- `regenerate_count` (PositiveSmallIntegerField): Contador de regeneraciones (máx 3)
- `scenario` (ForeignKey): Ahora es nullable para soportar escenarios dinámicos

```python
scenario_generated = models.JSONField(null=True, blank=True)
regenerate_count = models.PositiveSmallIntegerField(default=0)
scenario = models.ForeignKey(..., null=True, blank=True)
```

### 2. **core/services/roleplay_engine.py** - Nuevas funciones

#### `generate_dynamic_scenario(rol_it: str) -> dict`
- Llama a OpenAI (modelo: gpt-4o-mini)
- Genera un escenario personalizado basado en el rol IT
- Retorna JSON con estructura:
  ```json
  {
    "title": "Título del escenario",
    "context": "Contexto detallado...",
    "user_role": "Backend Developer",
    "bot_role": "Gerente de Proyecto",
    "initial_bot_message": "Mensaje inicial del bot",
    "max_turns": 4
  }
  ```

#### `generate_system_prompt(scenario, rol_it_sesion=None) -> str`
- **Refactorizada** para aceptar tanto `SoftskillsScenario` (BD) como `dict` (dinámicos)
- Extrae campos correctamente según el tipo de objeto
- Inyecta contexto de rol IT si está disponible

#### `process_turn()` - Actualizado
- Prioriza `scenario_generated` si existe
- Fallback a `scenario` para compatibilidad
- Extrae `max_turns` dinámicamente según el tipo

### 3. **core/controllers/roleplay_controller.py** - Nuevos endpoints

#### `POST /api/v1/roleplay/sessions/start/`
**Cambios clave:**
- Ya NO requiere `scenario_id`
- Ahora requiere `rol_it_sesion` en el body
- Llama automáticamente a `generate_dynamic_scenario(rol_it)`
- Almacena escenario en `scenario_generated` JSONField

**Body:**
```json
{ "rol_it_sesion": "backend" }
```

**Respuesta (201):**
```json
{
  "session_id": "uuid",
  "scenario": {
    "title": "...",
    "context": "...",
    "user_role": "...",
    "bot_role": "...",
    "max_turns": 4
  },
  "initial_bot_message": "..."
}
```

#### `POST /api/v1/roleplay/sessions/<uuid>/regenerate/` ✨ NUEVO
- Regenera un escenario diferente para la misma sesión
- Solo funciona si no se han intercambiado mensajes (solo existe mensaje inicial del bot)
- Máximo 3 regeneraciones por sesión
- Reinicia `chat_history` con nuevo escenario

**Respuesta (200):**
```json
{
  "scenario": { ... },
  "initial_bot_message": "...",
  "regenerate_count": 1,
  "can_regenerate": true
}
```

### 4. **core/urls.py** - Nueva ruta

```python
path('api/v1/roleplay/sessions/<uuid:session_id>/regenerate/', 
     views.roleplay_regenerate_scenario, 
     name='roleplay_regenerate_scenario'),
```

### 5. **core/migrations/0011_***.py** - Migración Django

Cambios de esquema:
- Agrega `scenario_generated` JSONField a `RoleplaySession`
- Agrega `regenerate_count` PositiveSmallIntegerField a `RoleplaySession`
- Modifica `scenario` ForeignKey para que sea nullable

---

## Cambios en el Frontend

### 1. **ScenarioSelector.vue** - Refactorización completa

**Antes:** 
- Mostraba lista de todos los escenarios predefinidos
- Categorías filtradas
- Modal de rol dentro del flujo

**Después:**
- Solo muestra `RoleSelector` modal
- Al seleccionar un rol, automáticamente:
  1. Llama a `POST /api/v1/roleplay/sessions/start/` con el rol
  2. Muestra spinner "Generando escenario personalizado..."
  3. Navega a `/roleplay/{sessionId}` con el escenario generado

**Código simplificado:**
```javascript
async function onRoleSelected(rolItSesion) {
  const res = await fetch('/api/v1/roleplay/sessions/start/', {
    method: 'POST',
    body: JSON.stringify({ rol_it_sesion: rolItSesion }),
  })
  const data = await res.json()
  store.initSession(data.session_id, data.scenario, data.initial_bot_message, rolItSesion)
  await router.push(`/roleplay/${data.session_id}`)
}
```

### 2. **useRoleplayStore.js** - Nueva acción

#### `regenerateScenario()`
- Llama a `POST /api/v1/roleplay/sessions/{id}/regenerate/`
- Actualiza `currentSession.scenario`
- Reinicia `messages` con nuevo mensaje inicial
- Resetea `turn_count` a 0
- Retorna `regenerate_count` y `can_regenerate`

```javascript
async regenerateScenario() {
  const res = await fetch(`.../regenerate/`, { method: 'POST' })
  const data = await res.json()
  this.currentSession.scenario = data.scenario
  this.messages = [{ role: 'assistant', content: data.initial_bot_message }]
  this.currentSession.turn_count = 0
  return data
}
```

### 3. **RoleplayChat.vue** - Botón de regeneración

**Header:**
- Muestra estado actual del rol IT (ej: "Tu rol: Backend Developer")
- Nuevo botón: "🔄 Regenerar (2 disponibles)" (solo visible si `turnCount === 0`)
- Button deshabilitado después de 3 regeneraciones

**Lógica:**
```javascript
async function regenerateScenario() {
  const confirmed = confirm('¿Regenerar escenario? (Tienes ' + (3 - regenerateCount.value) + ' disponibles)')
  if (!confirmed) return
  await store.regenerateScenario()
  regenerateCount.value += 1
  canRegenerate.value = regenerateCount.value < 3
}
```

---

## Flujo de Usuario

### Iniciar Nueva Sesión
```
1. Usuario navega a /roleplay
2. Ve modal: "Selecciona tu rol en IT"
3. Elige rol (ej: Backend Developer)
4. Sistema muestra: "Generando escenario personalizado..."
5. OpenAI genera escenario al azar
6. Chat carga con escenario generado
```

### Opción: Regenerar Escenario (Antes de Empezar)
```
1. Usuario ve botón "🔄 Regenerar (3 disponibles)"
2. Hace clic → confirma
3. Sistema genera nuevo escenario
4. Chat se reinicia con nuevo escenario
5. Botón ahora muestra "🔄 Regenerar (2 disponibles)"
6. Después de 3 regeneraciones, botón desaparece
```

### Iniciar Chat
```
1. Usuario escribe primer mensaje
2. Botón de regeneración desaparece (ya no se puede cambiar)
3. Chat procede normalmente hasta max_turns
4. Al final, genera informe de feedback
```

---

## API Contract

### Request/Response Examples

#### Crear Sesión con Escenario Dinámico
```bash
POST /api/v1/roleplay/sessions/start/
Content-Type: application/json
X-CSRFToken: <token>

{
  "rol_it_sesion": "backend"
}

---

HTTP/1.1 201 Created

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "scenario": {
    "title": "Resolución de Conflicto en Pair Programming",
    "context": "Tu compañero insiste en usar una arquitectura que consideras inapropiada...",
    "user_role": "Backend Developer",
    "bot_role": "Tech Lead",
    "max_turns": 4
  },
  "initial_bot_message": "Hey, vi que estás cuestionando mi propuesta. ¿Qué te preocupa?"
}
```

#### Regenerar Escenario
```bash
POST /api/v1/roleplay/sessions/550e8400-e29b-41d4-a716-446655440000/regenerate/
X-CSRFToken: <token>

---

HTTP/1.1 200 OK

{
  "scenario": {
    "title": "Negociación de Timeline con PM",
    "context": "El PM quiere terminar el feature en 1 semana...",
    "user_role": "Backend Developer",
    "bot_role": "Product Manager",
    "max_turns": 4
  },
  "initial_bot_message": "Necesitamos hablar sobre los deadlines del sprint...",
  "regenerate_count": 1,
  "can_regenerate": true
}
```

---

## Beneficios

| Aspecto | Anterior | Ahora |
|--------|----------|-------|
| **Escenarios** | Predefinidos en BD (limitados) | Generados dinámicamente (infinitos) |
| **Personalización** | Sin personalización por rol | Contextualizado por rol IT |
| **Almacenamiento** | Todos guardados en BD | Generados bajo demanda |
| **Costo** | Alto (DB queries) | Bajo (solo OpenAI API calls) |
| **Variedad** | Repetitivos | Diferentes cada vez |
| **Escalabilidad** | Limitada | Ilimitada |

---

## Testing

### Roles IT Disponibles
```
- frontend: Frontend Developer
- backend: Backend Developer
- fullstack: Fullstack Developer
- devops: DevOps Engineer
- data_engineer: Data Engineer
- qa: QA/Tester
- architect: Solutions Architect
- scrum_master: Scrum Master
- product_manager: Product Manager
- tech_lead: Tech Lead
- ml_engineer: ML/AI Engineer
- security: Security Engineer
- cloud_engineer: Cloud Engineer
```

### Test Users
13 usuarios de prueba predefinidos (uno por rol), cargables con:
```bash
python manage.py load_role_test_users --add-subscriptions
```

### Manual Testing Checklist
- [ ] Seleccionar un rol y verificar que se genera un escenario personalizado
- [ ] Confirmar que el escenario es diferente para cada rol
- [ ] Probar regeneración (max 3 veces)
- [ ] Verificar que botón desaparece después de escribir primer mensaje
- [ ] Completar un chat y verificar informe de feedback
- [ ] Cambiar de rol durante sesión con botón "Cambiar"

---

## Commits

- `36bd2b0` - Implementar generación dinámica de escenarios de roleplay con OpenAI y endpoint de regeneración
- `c4139a2` - Refactorizar frontend para usar escenarios dinámicos: regeneración, selector de roles simplificado

---

## Notas de Deployment

1. Ejecutar migraciones: `python manage.py migrate`
2. Compilar frontend: `cd frontend && npm run build`
3. El servidor debe tener OPENAI_API_KEY en env
4. Railway.app detecta pushes y deploya automáticamente
5. Para deployment manual, usar: `bash deploy.sh` en servidor
