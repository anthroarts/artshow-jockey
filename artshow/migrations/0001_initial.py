# -*- coding: utf-8 -*-


from django.db import models, migrations
import artshow.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('peeps', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('can_edit_spaces', models.BooleanField(default=False, help_text=b'Person is allowed to reserve or cancel spaces')),
                ('can_edit_pieces', models.BooleanField(default=False, help_text=b'Person is allowed to add, delete or change piece details')),
                ('can_deliver_pieces', models.BooleanField(default=False, help_text=b'Person is allowed to deliver pieces to the show')),
                ('can_retrieve_pieces', models.BooleanField(default=False, help_text=b'Person is allowed to retrieve pieces from the show')),
                ('can_arbitrate', models.BooleanField(default=False, help_text=b'Person is allowed to make executive decisions regarding pieces')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Allocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('requested', models.DecimalField(max_digits=4, decimal_places=1, validators=[artshow.models.validate_space])),
                ('allocated', models.DecimalField(default=0, max_digits=4, decimal_places=1, validators=[artshow.models.validate_space])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('artistid', models.IntegerField(serialize=False, verbose_name=b'artist ID', primary_key=True)),
                ('publicname', models.CharField(max_length=100, verbose_name=b'public name', blank=True)),
                ('website', models.URLField(blank=True)),
                ('mailin', models.BooleanField(default=False)),
                ('mailback_instructions', models.TextField(blank=True)),
                ('attending', models.BooleanField(default=True, help_text=b'is artist attending convention?')),
                ('reservationdate', models.DateField(null=True, blank=True)),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'permissions': (('is_artshow_staff', 'Can do generic art-show functions.'), ('is_artshow_kiosk', 'Can do kiosk functions.')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BatchScan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batchtype', models.IntegerField(default=0, choices=[(0, 'Unknown'), (1, 'Locations'), (2, 'Intermediate Bids'), (3, 'Final Bids'), (4, 'Bidder ID Allocation')])),
                ('data', models.TextField()),
                ('original_data', models.TextField(blank=True)),
                ('date_scanned', models.DateTimeField()),
                ('processed', models.BooleanField(default=False)),
                ('processing_log', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Bid',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=5, decimal_places=0)),
                ('buy_now_bid', models.BooleanField(default=False)),
                ('invalid', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Bidder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('at_con_contact', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('person', models.OneToOneField(to='peeps.Person', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BidderId',
            fields=[
                ('id', models.CharField(max_length=8, serialize=False, primary_key=True)),
                ('bidder', models.ForeignKey(to='artshow.Bidder', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Checkoff',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('shortname', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailSignature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('signature', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('subject', models.CharField(max_length=100)),
                ('template', models.TextField(help_text=b'Begin a line with "." to enable word-wrap. Use Django template language. Available variables: artist, pieces_in_show, payments, signature, artshow_settings. ')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('occurred', models.BooleanField(default=False)),
                ('auto_occur', models.DateTimeField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tax_paid', models.DecimalField(null=True, max_digits=7, decimal_places=2, blank=True)),
                ('paid_date', models.DateTimeField(null=True, blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('payer', models.ForeignKey(to='artshow.Bidder', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('price', models.DecimalField(max_digits=7, decimal_places=2)),
                ('invoice', models.ForeignKey(to='artshow.Invoice', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InvoicePayment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('payment_method', models.IntegerField(default=0, choices=[(0, 'Not Paid'), (1, 'Cash'), (2, 'Check'), (3, 'Card'), (4, 'Other')])),
                ('notes', models.CharField(max_length=100, blank=True)),
                ('invoice', models.ForeignKey(to='artshow.Invoice', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('description', models.CharField(max_length=100)),
                ('date', models.DateField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ChequePayment',
            fields=[
                ('payment_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='artshow.Payment', on_delete=models.CASCADE)),
                ('number', models.CharField(max_length=10, blank=True)),
                ('payee', models.CharField(max_length=100, blank=True)),
            ],
            options={
            },
            bases=('artshow.payment',),
        ),
        migrations.CreateModel(
            name='PaymentType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Piece',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pieceid', models.IntegerField()),
                ('code', models.CharField(max_length=10, editable=False)),
                ('name', models.CharField(max_length=100, verbose_name=b'title')),
                ('media', models.CharField(max_length=100, blank=True)),
                ('other_artist', models.CharField(help_text=b'Alternate artist name for this piece', max_length=100, blank=True)),
                ('condition', models.CharField(help_text=b'Condition of piece, if not "perfect".', max_length=100, blank=True)),
                ('location', models.CharField(max_length=8, blank=True)),
                ('not_for_sale', models.BooleanField(default=False)),
                ('adult', models.BooleanField(default=False)),
                ('min_bid', models.DecimalField(null=True, max_digits=5, decimal_places=0, blank=True)),
                ('buy_now', models.DecimalField(null=True, max_digits=5, decimal_places=0, blank=True)),
                ('voice_auction', models.BooleanField(default=False)),
                ('bidsheet_scanned', models.BooleanField(default=False)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('order', models.IntegerField(null=True, blank=True)),
                ('status', models.IntegerField(default=0, choices=[(0, 'Not In Show'), (5, 'Not In Show, Locked'), (1, 'In Show'), (2, 'Won'), (3, 'Sold'), (4, 'Returned')])),
                ('bid_sheet_printing', models.IntegerField(default=0, choices=[(0, 'Not Printed'), (1, 'To Be Printed'), (2, 'Printed')])),
                ('control_form_printing', models.IntegerField(default=0, choices=[(0, 'Not Printed'), (1, 'To Be Printed'), (2, 'Printed')])),
                ('artist', models.ForeignKey(to='artshow.Artist', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('productid', models.IntegerField()),
                ('name', models.CharField(max_length=100)),
                ('location', models.CharField(max_length=8, blank=True)),
                ('adult', models.BooleanField(default=False)),
                ('price', models.DecimalField(null=True, max_digits=5, decimal_places=2, blank=True)),
                ('artist', models.ForeignKey(to='artshow.Artist', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Space',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
                ('shortname', models.CharField(max_length=8)),
                ('description', models.TextField(blank=True)),
                ('allow_half_spaces', models.BooleanField(default=False)),
                ('available', models.DecimalField(max_digits=4, decimal_places=1, validators=[artshow.models.validate_space])),
                ('price', models.DecimalField(max_digits=4, decimal_places=2)),
                ('reservable', models.BooleanField(default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('summary', models.CharField(max_length=100)),
                ('detail', models.TextField(blank=True)),
                ('time_entered', models.DateTimeField()),
                ('done', models.BooleanField(default=False)),
                ('actor', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('due_at', models.ForeignKey(to='artshow.Event', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='piece',
            unique_together=set([('artist', 'pieceid')]),
        ),
        migrations.AddField(
            model_name='payment',
            name='artist',
            field=models.ForeignKey(to='artshow.Artist', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_type',
            field=models.ForeignKey(to='artshow.PaymentType', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='piece',
            field=models.OneToOneField(to='artshow.Piece', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bid',
            name='bidder',
            field=models.ForeignKey(to='artshow.Bidder', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bid',
            name='piece',
            field=models.ForeignKey(to='artshow.Piece', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='bid',
            unique_together=set([('piece', 'amount', 'invalid')]),
        ),
        migrations.AddField(
            model_name='artist',
            name='checkoffs',
            field=models.ManyToManyField(to='artshow.Checkoff', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='artist',
            name='payment_to',
            field=models.ForeignKey(related_name='receiving_payment_for', blank=True, to='peeps.Person', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='artist',
            name='person',
            field=models.ForeignKey(to='peeps.Person', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='artist',
            name='spaces',
            field=models.ManyToManyField(to='artshow.Space', through='artshow.Allocation'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='allocation',
            name='artist',
            field=models.ForeignKey(to='artshow.Artist', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='allocation',
            name='space',
            field=models.ForeignKey(to='artshow.Space', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='allocation',
            unique_together=set([('artist', 'space')]),
        ),
        migrations.AddField(
            model_name='agent',
            name='artist',
            field=models.ForeignKey(to='artshow.Artist', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='agent',
            name='person',
            field=models.ForeignKey(related_name='agent_for', to='peeps.Person', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
