from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_ebook_pdf_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='mentoriasubscription',
            name='billing_cycle',
            field=models.CharField(choices=[('monthly', 'Mensual'), ('bimonthly', 'Bimensual')], default='monthly', max_length=20),
        ),
    ]
