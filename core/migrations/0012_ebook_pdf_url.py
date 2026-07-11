from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_roleplaysession_regenerate_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ebook',
            name='pdf_url',
            field=models.URLField(blank=True, help_text='URL privada o firmada de descarga del PDF para compras por MercadoPago'),
        ),
    ]
