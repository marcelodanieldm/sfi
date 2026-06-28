from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_mentoria_mercadopago'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessedPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('gateway', models.CharField(
                    choices=[('stripe', 'Stripe'), ('mercadopago', 'MercadoPago')],
                    max_length=20,
                )),
                ('event_type', models.CharField(max_length=100)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name':        'Pago procesado',
                'verbose_name_plural': 'Pagos procesados',
                'ordering':            ['-processed_at'],
            },
        ),
    ]
