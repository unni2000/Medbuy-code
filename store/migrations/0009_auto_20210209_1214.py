# Generated by Django 3.1.5 on 2021-02-09 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_auto_20210209_1027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='quant',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
