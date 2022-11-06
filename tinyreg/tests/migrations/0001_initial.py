# Generated by Django 3.2.16 on 2022-10-24 01:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AuthorizationCode',
            fields=[
                ('code', models.CharField(max_length=100, primary_key=True, serialize=False)),
            ],
        ),
        migrations.CreateModel(
            name='BearerToken',
            fields=[
                ('token', models.CharField(max_length=100, primary_key=True, serialize=False)),
            ],
        ),
    ]