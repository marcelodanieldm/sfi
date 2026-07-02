import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_processedpayment'),
    ]

    operations = [
        migrations.CreateModel(
            name='SoftskillsScenario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(
                    choices=[
                        ('communication',     'Comunicación'),
                        ('leadership',        'Liderazgo'),
                        ('negotiation',       'Negociación'),
                        ('critical-thinking', 'Pensamiento crítico'),
                        ('innovation',        'Innovación'),
                        ('career',            'Desarrollo de carrera'),
                    ],
                    db_index=True,
                    max_length=30,
                )),
                ('title',               models.CharField(max_length=200)),
                ('context',             models.TextField()),
                ('user_role',           models.CharField(max_length=200)),
                ('bot_role',            models.CharField(max_length=200)),
                ('initial_bot_message', models.TextField()),
                ('max_turns',           models.PositiveSmallIntegerField(default=4)),
                ('created_at',          models.DateTimeField(auto_now_add=True)),
                ('updated_at',          models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name':        'Escenario de Roleplay',
                'verbose_name_plural': 'Escenarios de Roleplay',
                'ordering':            ['category', 'title'],
            },
        ),
        migrations.CreateModel(
            name='RoleplaySession',
            fields=[
                ('id',               models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status',           models.CharField(
                    choices=[('in_progress', 'En progreso'), ('completed', 'Completada')],
                    default='in_progress',
                    max_length=20,
                )),
                ('turn_count',       models.PositiveSmallIntegerField(default=0)),
                ('chat_history',     models.JSONField(default=list)),
                ('informe_feedback', models.TextField(blank=True, null=True)),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
                ('updated_at',       models.DateTimeField(auto_now=True)),
                ('scenario', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sessions',
                    to='core.softskillsscenario',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='roleplay_sessions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name':        'Sesión de Roleplay',
                'verbose_name_plural': 'Sesiones de Roleplay',
                'ordering':            ['-created_at'],
            },
        ),
    ]
