# Generated by Django 5.2 on 2025-04-22 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detalleventa',
            name='cantidad',
            field=models.DecimalField(decimal_places=3, max_digits=10),
        ),
    ]
