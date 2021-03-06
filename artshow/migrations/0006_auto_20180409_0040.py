# Generated by Django 2.0.4 on 2018-04-09 05:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('artshow', '0005_auto_20171228_2239'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='can_arbitrate',
            field=models.BooleanField(default=False, help_text='Person is allowed to make executive decisions regarding pieces'),
        ),
        migrations.AlterField(
            model_name='agent',
            name='can_deliver_pieces',
            field=models.BooleanField(default=False, help_text='Person is allowed to deliver pieces to the show'),
        ),
        migrations.AlterField(
            model_name='agent',
            name='can_edit_pieces',
            field=models.BooleanField(default=False, help_text='Person is allowed to add, delete or change piece details'),
        ),
        migrations.AlterField(
            model_name='agent',
            name='can_edit_spaces',
            field=models.BooleanField(default=False, help_text='Person is allowed to reserve or cancel spaces'),
        ),
        migrations.AlterField(
            model_name='agent',
            name='can_retrieve_pieces',
            field=models.BooleanField(default=False, help_text='Person is allowed to retrieve pieces from the show'),
        ),
        migrations.AlterField(
            model_name='artist',
            name='artistid',
            field=models.IntegerField(primary_key=True, serialize=False, verbose_name='artist ID'),
        ),
        migrations.AlterField(
            model_name='artist',
            name='attending',
            field=models.BooleanField(default=True, help_text='is artist attending convention?'),
        ),
        migrations.AlterField(
            model_name='artist',
            name='publicname',
            field=models.CharField(blank=True, max_length=100, verbose_name='public name'),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='template',
            field=models.TextField(help_text='Begin a line with "." to enable word-wrap. Use Django template language. Available variables: artist, pieces_in_show, payments, signature, artshow_settings. '),
        ),
        migrations.AlterField(
            model_name='piece',
            name='condition',
            field=models.CharField(blank=True, help_text='Condition of piece, if not "perfect".', max_length=100),
        ),
        migrations.AlterField(
            model_name='piece',
            name='name',
            field=models.CharField(max_length=100, verbose_name='title'),
        ),
        migrations.AlterField(
            model_name='piece',
            name='other_artist',
            field=models.CharField(blank=True, help_text='Alternate artist name for this piece', max_length=100),
        ),
    ]
