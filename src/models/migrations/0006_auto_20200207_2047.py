# Generated by Django 2.2.7 on 2020-02-08 01:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("models", "0005_customer_historical_route"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customer",
            name="historical_route",
            field=models.CharField(default="", max_length=100, null=True),
        ),
    ]
