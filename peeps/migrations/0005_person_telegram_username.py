# Generated by Django 5.1.4 on 2024-12-30 22:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('peeps', '0004_person_preferred_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='telegram_username',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
