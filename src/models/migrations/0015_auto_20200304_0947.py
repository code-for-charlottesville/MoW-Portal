# Generated by Django 2.2.7 on 2020-03-04 14:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0014_auto_20200304_0944'),
    ]

    operations = [
        migrations.AlterField(
            model_name='substitution',
            name='volunteer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='volunteer',
                to='models.Volunteer'),
        ),
    ]