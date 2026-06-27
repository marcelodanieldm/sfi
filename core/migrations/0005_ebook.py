from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_ebookorder'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ebook',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo',            models.CharField(max_length=200)),
                ('slug',              models.SlugField(max_length=220, unique=True)),
                ('descripcion',       models.TextField()),
                ('descripcion_corta', models.CharField(blank=True, max_length=300)),
                ('portada_url',       models.URLField(help_text='URL pública de la imagen de portada (Cloudinary, S3, etc.)')),
                ('hotlink_url',       models.URLField(help_text='HotLink de checkout generado en el dashboard de Hotmart')),
                ('hotmart_product_id', models.CharField(blank=True, db_index=True, help_text='ID del producto en Hotmart — usado para vincular con EbookOrder', max_length=50)),
                ('precio_usd',        models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('activo',            models.BooleanField(default=True)),
                ('orden',             models.PositiveSmallIntegerField(default=0)),
                ('created_at',        models.DateTimeField(auto_now_add=True)),
                ('updated_at',        models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name':        'eBook',
                'verbose_name_plural': 'eBooks',
                'ordering':            ['orden', 'titulo'],
            },
        ),
    ]
