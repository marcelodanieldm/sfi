"""
Crea un usuario de prueba con suscripción activa de mentorIA.

Uso:
  python manage.py create_test_user
  python manage.py create_test_user --email demo@skillsforit.com --password Demo1234!
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import MentorIASubscription, User


class Command(BaseCommand):
    help = 'Crea un usuario de prueba con acceso gratuito a mentorIA'

    def add_arguments(self, parser):
        parser.add_argument('--email',    default='demo@skillsforit.com')
        parser.add_argument('--password', default='Demo1234!')

    def handle(self, *args, **options):
        email    = options['email']
        password = options['password']

        # Crear o actualizar usuario
        user, created = User.objects.update_or_create(
            email=email,
            defaults={'username': email.split('@')[0], 'is_active': True},
        )
        user.set_password(password)
        user.save()

        # Crear o actualizar suscripción activa sin pasarela real
        MentorIASubscription.objects.update_or_create(
            user=user,
            defaults={
                'payment_provider':       'stripe',
                'stripe_customer_id':     'cus_test_free',
                'stripe_subscription_id': 'sub_test_free',
                'status':                 'active',
                'current_period_end':     timezone.now() + timezone.timedelta(days=3650),
            },
        )

        action = 'Creado' if created else 'Actualizado'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action} usuario de prueba:\n'
            f'  Email:       {email}\n'
            f'  Contraseña:  {password}\n'
            f'  Acceso:      mentorIA activo (10 años)\n'
        ))
