# Generated by Django 2.2.7 on 2020-03-17 04:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0018_auto_20200316_2125'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='job',
            options={'ordering': ['route__number', 'job_type', 'name']},
        ),
    ]
