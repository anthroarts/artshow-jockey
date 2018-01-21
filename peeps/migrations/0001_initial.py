# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('address1', models.CharField(max_length=100, verbose_name=b'address', blank=True)),
                ('address2', models.CharField(max_length=100, verbose_name=b'address line 2', blank=True)),
                ('city', models.CharField(max_length=100, blank=True)),
                ('state', models.CharField(max_length=40, blank=True)),
                ('postcode', models.CharField(max_length=20, blank=True)),
                ('country', models.CharField(max_length=40, blank=True)),
                ('phone', models.CharField(max_length=40, blank=True)),
                ('email', models.CharField(max_length=100, blank=True)),
                ('reg_id', models.CharField(max_length=40, verbose_name=b'Reg ID', blank=True)),
                ('comment', models.CharField(max_length=100, blank=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name_plural': 'People',
            },
            bases=(models.Model,),
        ),
    ]
