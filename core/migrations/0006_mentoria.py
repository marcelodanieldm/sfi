import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_ebook'),
    ]

    operations = [
        migrations.CreateModel(
            name='MentorIASubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_customer_id', models.CharField(blank=True, max_length=100)),
                ('stripe_subscription_id', models.CharField(blank=True, db_index=True, max_length=100)),
                ('status', models.CharField(
                    choices=[
                        ('active',   'Activa'),
                        ('inactive', 'Inactiva'),
                        ('canceled', 'Cancelada'),
                        ('past_due', 'Pago vencido'),
                        ('trialing', 'En prueba'),
                    ],
                    default='inactive',
                    max_length=20,
                )),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mentoria_subscription',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name':        'Suscripción MentorIA',
                'verbose_name_plural': 'Suscripciones MentorIA',
                'ordering':            ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MentorIASession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tipo', models.CharField(
                    choices=[
                        ('entrevistas',    'Entrevistas de trabajo'),
                        ('resolucion',     'Resolución de problemas'),
                        ('trabajo_equipo', 'Trabajo en equipo'),
                        ('comunicacion',   'Comunicación asertiva'),
                        ('proactividad',   'Proactividad'),
                    ],
                    max_length=30,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mentoria_sessions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name':        'Sesión MentorIA',
                'verbose_name_plural': 'Sesiones MentorIA',
                'ordering':            ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MentorIAMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rol', models.CharField(
                    choices=[('user', 'Usuario'), ('assistant', 'MentorIA')],
                    max_length=10,
                )),
                ('contenido', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages',
                    to='core.mentoriasession',
                )),
            ],
            options={
                'verbose_name':        'Mensaje MentorIA',
                'verbose_name_plural': 'Mensajes MentorIA',
                'ordering':            ['created_at'],
            },
        ),
    ]
