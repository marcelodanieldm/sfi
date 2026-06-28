from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


# ─────────────────────────────────────────────
#  Custom User Model
#  UUID pk · email único · created_at
# ─────────────────────────────────────────────
class User(AbstractUser):
    """
    Usuario personalizado.
    - id: UUID autogenerado (pk)
    - email: único, requerido
    - created_at: timestamp de registro (auto)
    - Hereda username, password, is_staff, is_superuser, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']

    def __str__(self):
        return self.email or self.username


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


class Habilidad(models.Model):
    NIVEL_CHOICES = [
        ('basico', 'Básico'),
        ('intermedio', 'Intermedio'),
        ('avanzado', 'Avanzado'),
    ]

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='basico')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='habilidades')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Habilidad'
        verbose_name_plural = 'Habilidades'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.get_nivel_display()})'


class Mentor(models.Model):
    nombre = models.CharField(max_length=200)
    especialidad = models.CharField(max_length=200)
    bio = models.TextField()
    foto_url = models.URLField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Mentor'
        verbose_name_plural = 'Mentores'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class MentoriaReserva(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='reservas')
    nombre = models.CharField(max_length=200)
    email = models.EmailField()
    fecha = models.DateField()
    hora = models.CharField(max_length=10)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva de Mentoría'
        verbose_name_plural = 'Reservas de Mentorías'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.nombre} con {self.mentor.nombre} ({self.fecha})'


class SuscripcionPremium(models.Model):
    PLAN_CHOICES = [
        ('mensual', 'Mensual - $9.99/mes'),
        ('anual', 'Anual - $79.99/año'),
    ]
    nombre = models.CharField(max_length=200)
    email = models.EmailField()
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='anual')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Suscripción Premium'
        verbose_name_plural = 'Suscripciones Premium'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f'{self.nombre} — {self.get_plan_display()}'


class CVAnalisis(models.Model):
    METODO_PAGO_CHOICES = [
        ('stripe', 'Stripe (USD)'),
        ('mercadopago', 'MercadoPago (ARS)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    archivo_nombre = models.CharField(max_length=255)
    jd_texto = models.TextField(blank=True)

    score_ats = models.PositiveSmallIntegerField(default=0)
    legibilidad_ok = models.BooleanField(default=True)
    problemas_formato = models.JSONField(default=list)
    keywords_encontradas = models.JSONField(default=list)
    keywords_faltantes = models.JSONField(default=list)
    secciones_presentes = models.JSONField(default=list)
    secciones_faltantes = models.JSONField(default=list)

    pagado = models.BooleanField(default=False)
    metodo_pago = models.CharField(max_length=20, blank=True, choices=METODO_PAGO_CHOICES)
    email = models.EmailField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Análisis de CV'
        verbose_name_plural = 'Análisis de CVs'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.archivo_nombre} — {self.score_ats}/100'


# ─────────────────────────────────────────────
#  AnalysisReport
#  Arquitectura de datos para el flujo ATS
#  con soporte de usuario autenticado,
#  contenido free/paid y trazabilidad de pago.
# ─────────────────────────────────────────────
class AnalysisReport(models.Model):
    # ── Identidad ──────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # CASCADE: si se elimina el usuario, se eliminan sus reportes.
    # null=True / blank=True para sesiones anónimas.
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='analysis_reports',
    )

    # ── Inputs ─────────────────────────────────
    cv_raw_text     = models.TextField()
    job_description = models.TextField(null=True, blank=True)

    # ── Resultado ATS ──────────────────────────
    ats_score = models.IntegerField(default=0)

    # ── Control de Pago ────────────────────────
    is_paid         = models.BooleanField(default=False)
    payment_gateway = models.CharField(max_length=20, null=True, blank=True)  # 'stripe' | 'mercadopago'
    payment_id      = models.CharField(max_length=100, null=True, blank=True)

    # ── Estructuras de la IA ───────────────────
    # free_content:  parsing_issues, keyword_match, section_check
    free_content = models.JSONField(default=dict)
    # paid_content:  tailored_summary, actionable_fixes
    paid_content = models.JSONField(default=dict, blank=True)

    # ── Auditoría ──────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reporte de Análisis'
        verbose_name_plural = 'Reportes de Análisis'
        ordering = ['-created_at']

    def __str__(self):
        return f'Report {self.id} - Score: {self.ats_score} - Paid: {self.is_paid}'

    # ── Helpers de acceso a JSONFields ─────────
    @property
    def parsing_issues(self):
        return self.free_content.get('parsing_issues', [])

    @property
    def keywords_found(self):
        return self.free_content.get('keyword_match', {}).get('found', [])

    @property
    def keywords_missing(self):
        return self.free_content.get('keyword_match', {}).get('missing', [])

    @property
    def section_check(self):
        return self.free_content.get('section_check', {})

    @property
    def tailored_summary(self):
        return self.paid_content.get('tailored_summary', '')

    @property
    def actionable_fixes(self):
        return self.paid_content.get('actionable_fixes', [])


# ─────────────────────────────────────────────
#  Ebook
#  Catálogo de eBooks vendidos vía Hotmart.
#  Sin almacenamiento de PDF: la entrega la
#  gestiona Hotmart a través del HotLink.
# ─────────────────────────────────────────────
class Ebook(models.Model):
    # ── Metadatos comerciales ───────────────
    titulo           = models.CharField(max_length=200)
    slug             = models.SlugField(max_length=220, unique=True)
    descripcion      = models.TextField()
    descripcion_corta = models.CharField(max_length=300, blank=True)
    portada_url      = models.URLField(help_text='URL pública de la imagen de portada (Cloudinary, S3, etc.)')

    # ── Checkout Hotmart ────────────────────
    hotlink_url        = models.URLField(help_text='HotLink de checkout generado en el dashboard de Hotmart')
    hotmart_product_id = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text='ID del producto en Hotmart — usado para vincular con EbookOrder',
    )

    # ── Precio (solo visualización en catálogo) ──
    precio_usd = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # ── Control ─────────────────────────────
    activo     = models.BooleanField(default=True)
    orden      = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'eBook'
        verbose_name_plural = 'eBooks'
        ordering            = ['orden', 'titulo']

    def __str__(self):
        return self.titulo


# ─────────────────────────────────────────────
#  EbookOrder
#  Registra cada compra aprobada desde Hotmart.
#  El pago y la entrega del PDF ocurren en Hotmart;
#  aquí guardamos al comprador para retención.
# ─────────────────────────────────────────────
class EbookOrder(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pendiente'),
        ('approved',   'Aprobado'),
        ('cancelled',  'Cancelado'),
        ('refunded',   'Reembolsado'),
        ('chargeback', 'Contracargo'),
    ]

    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hotmart_transaction = models.CharField(max_length=100, unique=True, db_index=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Producto Hotmart
    hotmart_product_id  = models.CharField(max_length=50, blank=True)
    hotmart_offer_code  = models.CharField(max_length=50, blank=True)

    # Datos del comprador (base para retención)
    buyer_email       = models.EmailField(db_index=True)
    buyer_name        = models.CharField(max_length=200, blank=True)
    buyer_first_name  = models.CharField(max_length=100, blank=True)
    buyer_last_name   = models.CharField(max_length=100, blank=True)
    buyer_phone       = models.CharField(max_length=30, blank=True)
    buyer_document    = models.CharField(max_length=50, blank=True)
    buyer_country     = models.CharField(max_length=100, blank=True)
    buyer_country_iso = models.CharField(max_length=5, blank=True)

    # Finanzas
    purchase_price    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_currency = models.CharField(max_length=10, blank=True)

    # Payload completo de Hotmart (auditoría)
    hotmart_payload = models.JSONField(default=dict)

    approved_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Orden de Ebook'
        verbose_name_plural = 'Órdenes de Ebook'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.hotmart_transaction} — {self.buyer_email} [{self.get_status_display()}]'


# ─────────────────────────────────────────────
#  MentorIA
#  Coach de Soft Skills IT disponible 24/7.
#  Suscripción mensual via Stripe + chat con IA.
# ─────────────────────────────────────────────
class MentorIASubscription(models.Model):
    STATUS_CHOICES = [
        ('active',    'Activa'),
        ('inactive',  'Inactiva'),
        ('canceled',  'Cancelada'),
        ('past_due',  'Pago vencido'),
        ('trialing',  'En prueba'),
    ]

    PROVIDER_CHOICES = [('stripe', 'Stripe'), ('mercadopago', 'MercadoPago')]

    user                   = models.OneToOneField('core.User', on_delete=models.CASCADE, related_name='mentoria_subscription')
    payment_provider       = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='stripe', blank=True)

    # Stripe
    stripe_customer_id     = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, db_index=True)

    # MercadoPago
    mp_preapproval_id      = models.CharField(max_length=100, blank=True, db_index=True)
    mp_payer_id            = models.CharField(max_length=100, blank=True)

    status                 = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    current_period_end     = models.DateTimeField(null=True, blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    updated_at             = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Suscripción MentorIA'
        verbose_name_plural = 'Suscripciones MentorIA'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.get_status_display()}'

    @property
    def is_active(self):
        from django.utils import timezone
        if self.status != 'active':
            return False
        if self.current_period_end and self.current_period_end < timezone.now():
            return False
        return True


class MentorIASession(models.Model):
    TIPO_CHOICES = [
        ('entrevistas',    'Entrevistas de trabajo'),
        ('resolucion',     'Resolución de problemas'),
        ('trabajo_equipo', 'Trabajo en equipo'),
        ('comunicacion',   'Comunicación asertiva'),
        ('proactividad',   'Proactividad'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='mentoria_sessions')
    tipo       = models.CharField(max_length=30, choices=TIPO_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Sesión MentorIA'
        verbose_name_plural = 'Sesiones MentorIA'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.get_tipo_display()} ({self.created_at.date()})'


class MentorIAMessage(models.Model):
    ROL_CHOICES = [('user', 'Usuario'), ('assistant', 'MentorIA')]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session    = models.ForeignKey(MentorIASession, on_delete=models.CASCADE, related_name='messages')
    rol        = models.CharField(max_length=10, choices=ROL_CHOICES)
    contenido  = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Mensaje MentorIA'
        verbose_name_plural = 'Mensajes MentorIA'
        ordering            = ['created_at']

    def __str__(self):
        return f'[{self.rol}] {self.contenido[:60]}'

