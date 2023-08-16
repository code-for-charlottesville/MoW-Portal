# Generated by Django 2.2.7 on 2020-03-01 05:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0010_volunteerrecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='volunteerrecord',
            name='is_substitution',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='volunteerrecord',
            unique_together={('volunteer', 'job', 'date')},
        ),
    ]