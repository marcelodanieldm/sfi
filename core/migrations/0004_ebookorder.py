import uuid
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_update_analysisreport_schema'),
    ]

    operations = [
        migrations.CreateModel(
            name='EbookOrder',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('hotmart_transaction', models.CharField(db_index=True, max_length=100, unique=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending',    'Pendiente'),
                        ('approved',   'Aprobado'),
                        ('cancelled',  'Cancelado'),
                        ('refunded',   'Reembolsado'),
                        ('chargeback', 'Contracargo'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('hotmart_product_id',  models.CharField(blank=True, max_length=50)),
                ('hotmart_offer_code',  models.CharField(blank=True, max_length=50)),
                ('buyer_email',         models.EmailField(db_index=True, max_length=254)),
                ('buyer_name',          models.CharField(blank=True, max_length=200)),
                ('buyer_first_name',    models.CharField(blank=True, max_length=100)),
                ('buyer_last_name',     models.CharField(blank=True, max_length=100)),
                ('buyer_phone',         models.CharField(blank=True, max_length=30)),
                ('buyer_document',      models.CharField(blank=True, max_length=50)),
                ('buyer_country',       models.CharField(blank=True, max_length=100)),
                ('buyer_country_iso',   models.CharField(blank=True, max_length=5)),
                ('purchase_price',      models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('purchase_currency',   models.CharField(blank=True, max_length=10)),
                ('hotmart_payload',     models.JSONField(default=dict)),
                ('approved_at',         models.DateTimeField(blank=True, null=True)),
                ('created_at',          models.DateTimeField(auto_now_add=True)),
                ('updated_at',          models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name':        'Orden de Ebook',
                'verbose_name_plural': 'Órdenes de Ebook',
                'ordering':            ['-created_at'],
            },
        ),
    ]
