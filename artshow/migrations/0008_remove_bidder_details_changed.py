# Generated by Django 2.0.8 on 2018-09-03 00:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('artshow', '0007_piece_reproduction_rights_included'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bidder',
            name='details_changed',
        ),
    ]
