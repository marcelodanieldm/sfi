"""
Management command para crear usuarios de prueba con diferentes roles IT.

Uso:
    python manage.py load_role_test_users [--add-subscriptions] [--skip-existing]

Opciones:
    --add-subscriptions    Crear suscripciones activas para los usuarios
    --skip-existing        No recrear usuarios si ya existen
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import sys

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga usuarios de prueba con todos los roles IT disponibles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--add-subscriptions',
            action='store_true',
            help='Crear suscripciones activas MentorIA para los usuarios',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='No recrear usuarios si ya existen',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Cargando usuarios de prueba con roles IT...\n'))

        # Definir usuarios de prueba
        test_users = [
            {
                'username': 'frontend_dev',
                'email': 'frontend@test.com',
                'first_name': 'Ana',
                'last_name': 'López',
                'rol_it': 'frontend',
            },
            {
                'username': 'backend_dev',
                'email': 'backend@test.com',
                'first_name': 'Carlos',
                'last_name': 'Gómez',
                'rol_it': 'backend',
            },
            {
                'username': 'fullstack_dev',
                'email': 'fullstack@test.com',
                'first_name': 'María',
                'last_name': 'Fernández',
                'rol_it': 'fullstack',
            },
            {
                'username': 'devops_eng',
                'email': 'devops@test.com',
                'first_name': 'Juan',
                'last_name': 'Martínez',
                'rol_it': 'devops',
            },
            {
                'username': 'data_engineer',
                'email': 'data@test.com',
                'first_name': 'Roberto',
                'last_name': 'Silva',
                'rol_it': 'data_engineer',
            },
            {
                'username': 'qa_tester',
                'email': 'qa@test.com',
                'first_name': 'Patricia',
                'last_name': 'García',
                'rol_it': 'qa',
            },
            {
                'username': 'architect',
                'email': 'architect@test.com',
                'first_name': 'Diego',
                'last_name': 'Rodríguez',
                'rol_it': 'architect',
            },
            {
                'username': 'scrum_master',
                'email': 'scrum@test.com',
                'first_name': 'Adriana',
                'last_name': 'López',
                'rol_it': 'scrum_master',
            },
            {
                'username': 'product_mgr',
                'email': 'product@test.com',
                'first_name': 'Santiago',
                'last_name': 'Pérez',
                'rol_it': 'product_manager',
            },
            {
                'username': 'tech_lead',
                'email': 'techlead@test.com',
                'first_name': 'Gabriela',
                'last_name': 'Torres',
                'rol_it': 'tech_lead',
            },
            {
                'username': 'ml_engineer',
                'email': 'ml@test.com',
                'first_name': 'Fernando',
                'last_name': 'Cruz',
                'rol_it': 'ml_engineer',
            },
            {
                'username': 'security_eng',
                'email': 'security@test.com',
                'first_name': 'Valeria',
                'last_name': 'Morales',
                'rol_it': 'security',
            },
            {
                'username': 'cloud_engineer',
                'email': 'cloud@test.com',
                'first_name': 'Andrés',
                'last_name': 'Ramírez',
                'rol_it': 'cloud_engineer',
            },
        ]

        created_count = 0
        updated_count = 0
        skip_existing = options.get('skip_existing', False)
        add_subscriptions = options.get('add_subscriptions', False)

        # Crear usuarios
        for user_data in test_users:
            rol_it = user_data.pop('rol_it')
            email = user_data['email']

            try:
                user = User.objects.get(email=email)
                if skip_existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⏭️  {email} ya existe (omitiendo)"
                        )
                    )
                    continue
                # Actualizar rol si ya existe
                user.rol_it_preferido = rol_it
                user.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  🔄 {email} actualizado con rol: {rol_it}"
                    )
                )
            except User.DoesNotExist:
                # Crear nuevo usuario
                user = User.objects.create_user(
                    password='test123456',
                    rol_it_preferido=rol_it,
                    **user_data
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ {email} creado con rol: {rol_it}"
                    )
                )

        # Agregar suscripciones si se solicita
        if add_subscriptions:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n💳 Agregando suscripciones MentorIA...\n'
                )
            )
            from core.models import MentorIASubscription

            subscription_created = 0
            for user_data in test_users:
                email = user_data['email']
                try:
                    user = User.objects.get(email=email)
                    subscription, created = MentorIASubscription.objects.get_or_create(
                        user=user,
                        defaults={
                            'is_active': True,
                            'provider': 'stripe',
                            'provider_subscription_id': f'test-sub-{email}',
                            'renewal_date': timezone.now() + timedelta(days=30),
                        }
                    )
                    if created:
                        subscription_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✅ Suscripción creada para {email}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ℹ️  {email} ya tiene suscripción"
                            )
                        )
                except User.DoesNotExist:
                    pass

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n  📊 {subscription_created} suscripción(es) creada(s)\n"
                )
            )

        # Resumen
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✨ Proceso completado:\n'
                f'  📝 {created_count} usuario(s) creado(s)\n'
                f'  🔄 {updated_count} usuario(s) actualizado(s)\n'
            )
        )

        self.stdout.write(
            self.style.WARNING(
                '⚠️  Nota: Todos los usuarios usan contraseña: test123456\n'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                '🧪 Usuarios de prueba listos para testing!\n'
                '   Prueba con: frontend@test.com, backend@test.com, etc.\n'
            )
        )
