from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_mentoria'),
    ]

    operations = [
        migrations.AddField(
            model_name='mentoriasubscription',
            name='payment_provider',
            field=models.CharField(
                blank=True,
                choices=[('stripe', 'Stripe'), ('mercadopago', 'MercadoPago')],
                default='stripe',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='mentoriasubscription',
            name='mp_preapproval_id',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name='mentoriasubscription',
            name='mp_payer_id',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
