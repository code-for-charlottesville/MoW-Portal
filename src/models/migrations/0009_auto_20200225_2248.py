# Generated by Django 2.2.7 on 2020-02-26 03:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0008_merge_20200212_1354'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='lae',
            field=models.FloatField(blank=True, default=0),
        ),
        migrations.AddField(
            model_name='customer',
            name='lon',
            field=models.FloatField(blank=True, default=0),
        ),
    ]
