"""
Envía recordatorios de renovación a suscriptores de MentorIA cuya suscripción
vence en los próximos DAYS_BEFORE días (default: 3).

Uso:
    python manage.py send_renewal_reminders
    python manage.py send_renewal_reminders --days 5

Configurar en cron (ejecutar diariamente):
    0 9 * * * /var/www/sfi/venv/bin/python /var/www/sfi/manage.py send_renewal_reminders
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import MentorIASubscription
from core.services.email_service import send_renewal_reminder_email


class Command(BaseCommand):
    help = 'Envía recordatorios de renovación a suscriptores de MentorIA'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Días de antelación para enviar el recordatorio (default: 3)',
        )

    def handle(self, *args, **options):
        days_before = options['days']
        now = timezone.now()
        window_start = now + timedelta(days=days_before - 1)
        window_end = now + timedelta(days=days_before)

        subs = MentorIASubscription.objects.filter(
            status='active',
            current_period_end__gte=window_start,
            current_period_end__lt=window_end,
        ).select_related('user')

        sent = 0
        for sub in subs:
            days_left = (sub.current_period_end - now).days + 1
            ok = send_renewal_reminder_email(
                user=sub.user,
                provider=sub.payment_provider or 'stripe',
                period_end=sub.current_period_end,
                days_until_renewal=days_left,
            )
            if ok:
                sent += 1
                self.stdout.write(f'  ✓ {sub.user.email} ({sub.payment_provider})')
            else:
                self.stderr.write(f'  ✗ {sub.user.email} — error al enviar')

        self.stdout.write(self.style.SUCCESS(f'Recordatorios enviados: {sent}/{subs.count()}'))
