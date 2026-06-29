"""
Crea un usuario de prueba con suscripción activa de mentorIA.

Uso:
  python manage.py create_test_user
  python manage.py create_test_user --email demo@skillsforit.com --password Demo1234!
  python manage.py create_test_user --superuser
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import MentorIASubscription, User


class Command(BaseCommand):
    help = 'Crea un usuario de prueba con acceso gratuito a mentorIA'

    def add_arguments(self, parser):
        parser.add_argument('--email',     default='demo@skillsforit.com')
        parser.add_argument('--password',  default='Demo1234!')
        parser.add_argument('--superuser', action='store_true',
                            help='Crear como superusuario (bypasea el chequeo de suscripción)')

    def handle(self, *args, **options):
        email      = options['email']
        password   = options['password']
        is_super   = options['superuser']

        defaults = {'username': email.split('@')[0], 'is_active': True}
        if is_super:
            defaults['is_staff']     = True
            defaults['is_superuser'] = True

        user, created = User.objects.update_or_create(email=email, defaults=defaults)
        user.set_password(password)
        user.save()

        # Solo crea suscripción si no es superusuario (el superusuario bypasea el check)
        if not is_super:
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
        role   = 'superusuario' if is_super else 'demo con suscripción activa (10 años)'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action} usuario:\n'
            f'  Email:       {email}\n'
            f'  Contraseña:  {password}\n'
            f'  Rol:         {role}\n'
            f'  Acceso chat: {"sí (bypass superusuario)" if is_super else "sí (suscripción activa)"}\n'
        ))
