# Generated by Django 2.2.7 on 2020-03-05 18:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0015_auto_20200304_0947'),
    ]

    operations = [
        migrations.AddField(
            model_name='volunteerrecord',
            name='is_substitution',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]