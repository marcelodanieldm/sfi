# SkillsForIT — Backend

Plataforma de formación para profesionales IT. Incluye un catálogo de eBooks vendidos vía Hotmart, un evaluador de CVs con IA y **mentorIA**, un coach de soft skills con suscripción mensual.

**Stack:** Python · Django 4.2 · OpenAI gpt-4o-mini · Stripe · MercadoPago · Hotmart

---

## Productos

### 1. eBook Catalog (`/ebook/`)
Landing page estática que muestra los eBooks disponibles. La entrega del PDF ocurre completamente en Hotmart — el backend solo registra al comprador para retención y estrategias de marketing.

### 2. ATS Evaluator (`/ats-evaluator/`)
Herramienta de análisis de CVs con IA. El usuario sube su CV, el sistema lo evalúa con dos agentes de IA (parsing + recomendaciones) y ofrece un informe premium detrás de un pago único (Stripe o MercadoPago).

### 3. MentorIA (`/mentoria/`)
Coach de soft skills IT disponible 24/7 por texto. Suscripción mensual de USD $9.99 procesada por Stripe o MercadoPago. El chat evalúa al usuario en 5 áreas con IA y genera un informe estructurado con la Respuesta Perfecta a nivel Staff/Principal Dev.

---

## Estructura del proyecto

```
sfi/
├── skillsforit/          # Configuración Django (settings, urls, wsgi)
├── core/
│   ├── models.py         # Todos los modelos de la aplicación
│   ├── views.py          # Re-exports de controladores
│   ├── urls.py           # Routing completo
│   ├── admin.py          # Panel de administración
│   ├── controllers/      # Lógica de negocio por dominio
│   │   ├── auth_controller.py            # Login + Registro
│   │   ├── ebook_controller.py           # Landing de eBooks
│   │   ├── hotmart_controller.py         # Webhook de Hotmart
│   │   ├── mentor_ia_controller.py       # Chat, checkout y API de MentorIA
│   │   ├── payments_controller.py        # Endpoints unificados de pago
│   │   ├── stripe_webhook_controller.py  # Webhook dedicado de Stripe
│   │   ├── mercadopago_webhook_controller.py  # Webhook dedicado de MP
│   │   └── unified_webhook_controller.py # Webhook unificado con idempotencia
│   ├── services/
│   │   ├── ai_agents.py      # Agentes de IA para el ATS Evaluator
│   │   ├── ats_engine.py     # Motor de puntuación ATS
│   │   ├── email_service.py  # Emails transaccionales via Resend
│   │   └── payment_service.py
│   ├── migrations/
│   └── templates/core/
│       ├── auth/             # Login / Registro / Reset de contraseña
│       ├── mentor_ia/        # Chat y landing de MentorIA (Django templates)
│       └── emails/           # Email de bienvenida post-compra eBook
├── ebook/                # Landing estática de eBooks (servida via FTP)
├── mentoria/             # Landing estática de MentorIA (servida via FTP)
├── passenger_wsgi.py     # Entry point para Donweb / cPanel Passenger
├── requirements.txt
└── manage.py
```

---

## Modelos principales

| Modelo | Descripción |
|--------|-------------|
| `User` | Usuario personalizado con UUID y email único |
| `Ebook` | Catálogo de eBooks (título, portada, HotLink, precio display) |
| `EbookOrder` | Compra aprobada desde Hotmart con datos del comprador |
| `AnalysisReport` | Reporte de análisis de CV (free + paid content en JSON) |
| `MentorIASubscription` | Suscripción activa de mentorIA (Stripe o MercadoPago) |
| `MentorIASession` | Sesión de evaluación por tipo (entrevistas, comunicación, etc.) |
| `MentorIAMessage` | Mensaje individual del chat (usuario o IA) |
| `ProcessedPayment` | Tabla de idempotencia para webhooks de pago |

---

## API Endpoints

### Autenticación
| Método | URL | Descripción |
|--------|-----|-------------|
| GET/POST | `/login/` | Login + Registro (tabs) |
| POST | `/logout/` | Cerrar sesión |

### MentorIA — Chat
| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/mentoria/` | Landing / paywall |
| GET | `/mentoria/chat/` | Interfaz de chat (requiere suscripción activa) |
| POST | `/mentoria/api/session/` | Crea sesión y obtiene mensaje inicial de la IA |
| POST | `/mentoria/api/message/<id>/` | Envía mensaje y recibe respuesta de la IA |

### Pagos — Checkout
| Método | URL | Descripción |
|--------|-----|-------------|
| POST | `/api/v1/payments/create-session` | URL de checkout (Stripe o MP) |
| POST | `/api/v1/payments/portal` | URL del portal de autogestión de Stripe |
| POST | `/mentoria/checkout/` | Checkout directo Stripe |
| POST | `/mentoria/mp/checkout/` | Checkout directo MercadoPago |

### Webhooks
| Método | URL | Descripción |
|--------|-----|-------------|
| POST | `/api/v1/webhooks/payments` | Webhook unificado (Stripe + MP) con idempotencia |
| POST | `/api/v1/webhooks/stripe/` | Webhook dedicado Stripe |
| POST | `/api/v1/webhooks/mercadopago/` | Webhook dedicado MercadoPago |
| POST | `/api/webhooks/hotmart/` | Webhook de Hotmart para eBooks |

### ATS Evaluator
| Método | URL | Descripción |
|--------|-----|-------------|
| GET/POST | `/ats-evaluator/` | Subir CV y generar análisis |
| GET | `/ats-evaluator/resultado/<uuid>/` | Resultado gratuito |
| GET/POST | `/ats-evaluator/checkout/<uuid>/pay/` | Pago del informe premium |
| GET | `/ats-evaluator/informe/<uuid>/` | Informe completo con IA |

---

## Seguridad de webhooks

El webhook unificado (`/api/v1/webhooks/payments`) detecta la pasarela por header HTTP:
- `Stripe-Signature` → valida con `stripe.Webhook.construct_event`
- `x-signature` → valida con HMAC-SHA256 (Notifications v2 de MP)

Antes de modificar la DB, verifica idempotencia en la tabla `ProcessedPayment`. Si el `event_id` ya existe, responde 200 sin procesar.

---

## Flujo de MentorIA

```
skillsforit.online/mentoria  (HTML estático)
  → /login/                  (Django — login o registro)
  → /mentoria/              (Django — paywall)
  → Stripe o MercadoPago     (checkout externo)
  → webhook activa suscripción en DB
  → /mentoria/chat/         (Django — chat con OpenAI gpt-4o-mini)
```

El chat bloquea el input mientras la IA genera el informe. El informe sigue esta estructura:

- **Aspectos Positivos** — qué hizo bien el usuario
- **La Respuesta Perfecta (Nivel Staff / Principal Dev)** — texto de élite
- **¿Por qué esta opción es mejor?** — psicología detrás de la respuesta

---

## Variables de entorno

```bash
# Django
SECRET_KEY=
DJANGO_SETTINGS_MODULE=skillsforit.settings
ALLOWED_HOSTS=skillsforit.online,.railway.app
DEBUG=False
SITE_URL=https://skillsforit.online

# IA — OpenAI
# Obtené tu key en: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-...

# Email (Resend)
RESEND_API_KEY=re_...
DEFAULT_FROM_EMAIL=SkillsForIT <info@skillsforit.com>
EBOOK_WELCOME_COUPON=SKILLS20

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_MENTORIA_PRICE_ID=price_...
STRIPE_MENTORIA_WEBHOOK_SECRET=whsec_...

# MercadoPago
MP_ACCESS_TOKEN=APP_USR-...
MP_WEBHOOK_SECRET=...
EBOOK_MP_AMOUNT=19990            # Pago único eBook por MercadoPago
EBOOK_MP_CURRENCY=ARS
MP_PREAPPROVAL_PLAN_ID=...       # Suscripción MentorIA; equivalente al Price ID de Stripe
MP_PREAPPROVAL_PLAN_ID_BIMONTHLY=...
MP_SUBSCRIPTION_AMOUNT=9990      # Suscripción MentorIA; solo si no usás Plan ID
MP_SUBSCRIPTION_AMOUNT_BIMONTHLY=59980
MP_SUBSCRIPTION_CURRENCY=ARS     # Suscripción MentorIA; solo si no usás Plan ID

# Hotmart
HOTMART_WEBHOOK_TOKEN=...
```

---

## Instalación local

```bash
git clone https://github.com/marcelodanieldm/sfi.git
cd sfi
pip install -r requirements.txt
cp .env.example .env        # copiar y completar variables (mínimo: OPENAI_API_KEY)
python manage.py migrate
python manage.py create_test_user   # crea demo@skillsforit.com con suscripción activa

# Usuarios de prueba con roles IT (opcional para testing roleplay)
python manage.py load_role_test_users --add-subscriptions
```

**Usuarios de prueba creados** (contraseña: `test123456`):
- `frontend@test.com` → Frontend Developer
- `backend@test.com` → Backend Developer
- `fullstack@test.com` → Fullstack Developer
- `devops@test.com` → DevOps Engineer
- `data@test.com` → Data Engineer
- `qa@test.com` → QA/Tester
- `architect@test.com` → Solutions Architect
- `scrum@test.com` → Scrum Master
- `product@test.com` → Product Manager
- `techlead@test.com` → Tech Lead
- `ml@test.com` → ML/AI Engineer
- `security@test.com` → Security Engineer
- `cloud@test.com` → Cloud Engineer

```bash
python manage.py runserver
```

---

## Deploy en Railway

1. railway.app → New Project → Deploy from GitHub → `marcelodanieldm/sfi`
2. Agregar `Procfile` en raíz: `web: gunicorn skillsforit.wsgi --bind 0.0.0.0:$PORT`
3. Configurar variables de entorno en Railway → Variables
4. Railway → Shell → `python manage.py migrate`
5. Settings → Custom Domain → `skillsforit.online`

## Deploy de landings estáticas (Donweb FTP)

Las landings de eBook y MentorIA son HTML/CSS puro sin Django:

| Archivo local | Subir a |
|---------------|---------|
| `ebook/index.html` | `/public_html/ebook/index.html` |
| `mentoria/index.html` | `/public_html/mentoria/index.html` |

---

## Configurar webhooks en producción

**Stripe** → Dashboard → Developers → Webhooks → Add endpoint:
- URL: `https://skillsforit.online/api/v1/webhooks/payments`
- Eventos: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`, `checkout.session.completed`

**MercadoPago** → Tus integraciones → Notificaciones:
- URL: `https://skillsforit.online/api/v1/webhooks/payments`
- Evento: Suscripciones (Preapproval)

**Hotmart** → Ferramentas → Webhooks:
- URL: `https://skillsforit.online/api/webhooks/hotmart/`
