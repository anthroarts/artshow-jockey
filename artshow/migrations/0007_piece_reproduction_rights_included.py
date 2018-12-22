# Generated by Django 2.0.8 on 2018-08-19 04:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('artshow', '0006_auto_20180409_0040'),
    ]

    operations = [
        migrations.AddField(
            model_name='piece',
            name='reproduction_rights_included',
            field=models.BooleanField(default=False, help_text='This sale includes reproduction rights to the piece.'),
        ),
    ]