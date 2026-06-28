from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core.models import User, Categoria, Habilidad, Mentor, MentoriaReserva, SuscripcionPremium, CVAnalisis, AnalysisReport, Ebook, EbookOrder, MentorIASubscription, MentorIASession, MentorIAMessage, ProcessedPayment


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'is_staff', 'is_superuser', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email']
    readonly_fields = ['id', 'created_at']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Info adicional', {'fields': ('created_at',)}),
    )


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre']


@admin.register(Habilidad)
class HabilidadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nivel', 'categoria', 'activo', 'fecha_creacion']
    list_filter = ['nivel', 'categoria', 'activo']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']


@admin.register(Mentor)
class MentorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'especialidad', 'activo', 'orden']
    list_editable = ['activo', 'orden']
    search_fields = ['nombre', 'especialidad']


@admin.register(MentoriaReserva)
class MentoriaReservaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'email', 'mentor', 'fecha', 'hora', 'estado', 'fecha_creacion']
    list_filter = ['estado', 'mentor']
    search_fields = ['nombre', 'email']
    list_editable = ['estado']


@admin.register(SuscripcionPremium)
class SuscripcionPremiumAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'email', 'plan', 'fecha_registro']
    list_filter = ['plan']
    search_fields = ['nombre', 'email']


@admin.register(CVAnalisis)
class CVAnalisisAdmin(admin.ModelAdmin):
    list_display = ['archivo_nombre', 'score_ats', 'pagado', 'metodo_pago', 'fecha']
    list_filter = ['pagado', 'metodo_pago']
    search_fields = ['archivo_nombre', 'email']
    readonly_fields = ['id', 'fecha']


@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display  = ['id', 'user', 'ats_score', 'is_paid', 'payment_gateway', 'created_at']
    list_filter   = ['is_paid', 'payment_gateway']
    search_fields = ['user__email', 'payment_id']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Identidad',      {'fields': ('id', 'user', 'created_at')}),
        ('Inputs',         {'fields': ('cv_raw_text', 'job_description')}),
        ('Resultado',      {'fields': ('ats_score',)}),
        ('Pago',           {'fields': ('is_paid', 'payment_gateway', 'payment_id')}),
        ('Contenido free', {'fields': ('free_content',)}),
        ('Contenido pago', {'fields': ('paid_content',)}),
    )


@admin.register(Ebook)
class EbookAdmin(admin.ModelAdmin):
    list_display       = ['titulo', 'precio_usd', 'activo', 'orden', 'updated_at']
    list_filter        = ['activo']
    list_editable      = ['activo', 'orden']
    search_fields      = ['titulo', 'slug', 'hotmart_product_id']
    prepopulated_fields = {'slug': ('titulo',)}
    readonly_fields    = ['created_at', 'updated_at']
    fieldsets = (
        ('Catálogo',  {'fields': ('titulo', 'slug', 'descripcion_corta', 'descripcion', 'portada_url', 'precio_usd')}),
        ('Hotmart',   {'fields': ('hotlink_url', 'hotmart_product_id')}),
        ('Control',   {'fields': ('activo', 'orden', 'created_at', 'updated_at')}),
    )


@admin.register(EbookOrder)
class EbookOrderAdmin(admin.ModelAdmin):
    list_display   = ['hotmart_transaction', 'buyer_email', 'buyer_name', 'status', 'purchase_price', 'purchase_currency', 'approved_at', 'created_at']
    list_filter    = ['status', 'purchase_currency', 'buyer_country_iso']
    search_fields  = ['hotmart_transaction', 'buyer_email', 'buyer_name', 'buyer_document']
    readonly_fields = ['id', 'created_at', 'updated_at', 'hotmart_payload']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Transacción', {'fields': ('id', 'hotmart_transaction', 'status', 'hotmart_product_id', 'hotmart_offer_code')}),
        ('Comprador',   {'fields': ('buyer_email', 'buyer_name', 'buyer_first_name', 'buyer_last_name', 'buyer_phone', 'buyer_document', 'buyer_country', 'buyer_country_iso')}),
        ('Financiero',  {'fields': ('purchase_price', 'purchase_currency')}),
        ('Auditoría',   {'fields': ('hotmart_payload', 'approved_at', 'created_at', 'updated_at')}),
    )


@admin.register(MentorIASubscription)
class MentorIASubscriptionAdmin(admin.ModelAdmin):
    list_display    = ['user', 'status', 'stripe_subscription_id', 'current_period_end', 'created_at']
    list_filter     = ['status']
    search_fields   = ['user__email', 'stripe_customer_id', 'stripe_subscription_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MentorIASession)
class MentorIASessionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'tipo', 'created_at']
    list_filter   = ['tipo']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(MentorIAMessage)
class MentorIAMessageAdmin(admin.ModelAdmin):
    list_display  = ['session', 'rol', 'contenido_short', 'created_at']
    list_filter   = ['rol']
    readonly_fields = ['id', 'created_at']

    def contenido_short(self, obj):
        return obj.contenido[:80]
    contenido_short.short_description = 'Contenido'


@admin.register(ProcessedPayment)
class ProcessedPaymentAdmin(admin.ModelAdmin):
    list_display   = ['event_id', 'gateway', 'event_type', 'processed_at']
    list_filter    = ['gateway', 'event_type']
    search_fields  = ['event_id']
    readonly_fields = ['event_id', 'gateway', 'event_type', 'processed_at']
    date_hierarchy = 'processed_at'
