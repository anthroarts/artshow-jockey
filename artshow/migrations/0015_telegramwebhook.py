# Generated by Django 5.1.4 on 2024-12-30 01:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('artshow', '0014_squareinvoicepayment_invoicepayment_complete_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramWebhook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('body', models.JSONField()),
            ],
        ),
    ]