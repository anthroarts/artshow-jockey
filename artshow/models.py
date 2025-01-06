# Artshow Jockey
# Copyright (C) 2009, 2010 Chris Cogdon
# See file COPYING for licence details

__all__ = ["Allocation", "Artist", "ArtistManager", "BatchScan", "Bid", "Bidder", "BidderId",
           "Checkoff", "ChequePayment", "EmailSignature", "EmailTemplate", "Event", "Invoice", "InvoiceItem",
           "InvoicePayment", "Payment", "PaymentType", "Piece", "Product", "Location", "Space", "Task",
           "Agent", "validate_space", "validate_space_increments"]

from decimal import Decimal

from django.db import models
from django.db.models import (
    Count, IntegerField, Max, OuterRef, Subquery, Sum, Q, Value as V
)
from django.db.models.functions import Cast, Coalesce, Substr
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from num2words import num2words

from . import mod11codes
from .conf import settings


def validate_space(value):
    if value < 0:
        raise ValidationError("Spaces must not be negative")


def validate_space_increments(value, allow_half_spaces):
    remainder = value % 1
    if remainder != 0 and (remainder != Decimal("0.5") or not allow_half_spaces):
        if allow_half_spaces:
            raise ValidationError("Spaces must be in whole, or half (0.5) increments")
        else:
            raise ValidationError("Spaces must be in whole increments")


# A type of space which an Artist can request.
class Space(models.Model):
    name = models.CharField(max_length=20)
    shortname = models.CharField(max_length=8)
    description = models.TextField(blank=True)
    allow_half_spaces = models. BooleanField(default=False)
    available = models.DecimalField(max_digits=4, decimal_places=1, validators=[validate_space])
    price = models.DecimalField(max_digits=4, decimal_places=2)
    reservable = models.BooleanField(default=True)

    def clean(self):
        validate_space_increments(self.available, self.allow_half_spaces)

    def allocated(self):
        allocated = self.allocation_set.aggregate(sum=Sum('allocated'))['sum']
        if allocated is None:
            return 0
        else:
            return allocated

    def remaining(self):
        return self.available - self.allocated()

    def waiting(self):
        data = self.allocation_set.aggregate(allocated=Sum('allocated'), requested=Sum('requested'))
        if data['allocated'] is None or data['requested'] is None:
            return 0
        else:
            return data['requested'] - data['allocated']

    def __str__(self):
        return self.name


class LocationManager(models.Manager):
    def sorted(self):
        return self.annotate(
            prefix=Substr('name', 1, 1),
            index=Cast(Substr('name', 2), IntegerField())
        ).order_by('prefix', 'index')


# A specific instance of a Space to which one or two Artists may be assigned.
class Location(models.Model):
    name = models.CharField(max_length=5)
    type = models.ForeignKey('Space', on_delete=models.CASCADE)
    artist_1 = models.ForeignKey('Artist', on_delete=models.SET_NULL,
                                 blank=True, null=True, related_name='+')
    artist_2 = models.ForeignKey('Artist', on_delete=models.SET_NULL,
                                 blank=True, null=True, related_name='+')
    half_space = models.BooleanField(
        default=False,
        help_text='''This location is a half-space that can only be allocated to a
            single artist.''')
    space_is_split = models.BooleanField(
        verbose_name='Split',
        default=False,
        help_text='Space counts as half for each artist.')

    objects = LocationManager()

    def __str__(self):
        return self.name

    def clean(self):
        if (self.space_is_split or self.half_space) and not self.type.allow_half_spaces:
            raise ValidationError('Allocating half-spaces not allowed for this type.')
        if self.space_is_split and self.half_space:
            raise ValidationError('A half space can\'t be split.')
        if self.artist_1 is not None and self.artist_2 is not None:
            if self.half_space:
                raise ValidationError('Cannot assign two artists to a half space.')
            if not self.space_is_split:
                raise ValidationError('A space with two artists must be split.')
            if self.artist_1 == self.artist_2:
                raise ValidationError('Cannot allocate the same artist to both halves.')


class Checkoff (models.Model):
    name = models.CharField(max_length=100)
    shortname = models.CharField(max_length=100)

    def __str__(self):
        return "%s (%s)" % (self.name, self.shortname)


class ArtistManager (models.Manager):
    def grants_access_to(self, user, **kwargs):
        accessors = Agent.objects.filter(person__user=user, **kwargs)
        # TODO. find out if "distinct" is really needed here
        return self.get_queryset().filter(Q(agent__in=accessors) | Q(person__user=user)).distinct()

    def viewable_by(self, user):
        accessors = Agent.objects.filter(person__user=user)
        # TODO. find out if "distinct" is really needed here
        return self.get_queryset().filter(Q(agent__in=accessors) | Q(person__user=user)).distinct()


class Artist (models.Model):

    objects = ArtistManager()

    artistid = models.IntegerField(primary_key=True, verbose_name="artist ID")
    person = models.ForeignKey(settings.ARTSHOW_PERSON_CLASS,
                               on_delete=models.CASCADE)

    def name(self):
        return self.person.name
    publicname = models.CharField(max_length=100, blank=True, verbose_name="public name")
    website = models.URLField(max_length=200, blank=True)
    mailin = models.BooleanField(default=False)
    mailback_instructions = models.TextField(blank=True)
    attending = models.BooleanField(default=True, help_text="is artist attending convention?")
    reservationdate = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    spaces = models.ManyToManyField(Space, through="Allocation")
    checkoffs = models.ManyToManyField(Checkoff, blank=True)
    payment_to = models.ForeignKey(settings.ARTSHOW_PERSON_CLASS, null=True,
                                   blank=True, on_delete=models.CASCADE,
                                   related_name="receiving_payment_for")

    def artistname(self):
        return self.publicname or self.person.name

    def is_showing(self):
        return self.allocation_set.aggregate(
            alloc=Coalesce(Sum('allocated'), V(0)))['alloc'] > 0

    def is_active(self):
        return self.allocation_set.aggregate(
            req=Coalesce(Sum('requested'), V(0)))['req'] > 0

    def requested_spaces(self):
        return ", ".join("%s:%s" % (al.space.shortname, al.requested) for al in self.allocation_set.all())

    def allocated_spaces(self):
        space_map = {}
        locations = Location.objects \
            .filter(Q(artist_1=self) | Q(artist_2=self)) \
            .select_related('type')
        for l in locations:
            size = 0.5 if l.space_is_split or l.half_space else 1.0
            if l.type.shortname in space_map:
                space_map[l.type.shortname] += size
            else:
                space_map[l.type.shortname] = size

        return ", ".join("%s:%s" % (shortname, allocated) for shortname, allocated in space_map.items())

    def assigned_locations(self):
        return [l[0] for l in Location.objects.sorted()
                                      .filter(Q(artist_1=self) | Q(artist_2=self))
                                      .values_list('name')]

    def used_locations(self):
        return [x[0] for x in self.piece_set.exclude(status__in=[Piece.StatusNotInShow, Piece.StatusNotInShowLocked])
                                  .distinct().values_list("location")]

    def balance(self):
        return self.payment_set.aggregate(balance=Sum('amount'))['balance'] or 0

    def deduction_remaining_with_details(self):
        """Calculate space fee reduction remaining. Takes into account spaces reserved, space fees already applied"""
        total_requested_cost = Decimal(0)
        for a in self.allocation_set.all():
            total_requested_cost += a.space.price * a.requested
        # Deductions from accounts are always negative, so we re-negate it.
        deduction_to_date = - (
            self.payment_set.filter(payment_type_id=settings.ARTSHOW_SPACE_FEE_PK).aggregate(amount=Sum("amount"))["amount"] or 0)
        deduction_remaining = max(total_requested_cost - deduction_to_date, 0)
        return total_requested_cost, deduction_to_date, deduction_remaining

    def payment_remaining_with_details(self):
        """Calculate remaining payment expected, based on negative balance, plus any space reservations as yet
        unaccounted for."""
        total_requested_cost, deduction_to_date, deduction_remaining = self.deduction_remaining_with_details()
        payment_remaining = max(deduction_remaining - self.balance(), 0)
        return total_requested_cost, deduction_to_date, deduction_remaining, payment_remaining

    def __str__(self):
        return "%s (%s)" % (self.artistname(), self.artistid)

    def chequename(self):
        if self.payment_to:
            return self.payment_to.name
        else:
            return self.person.name

    def grants_access_to(self, user, **kwargs):
        return self.person.user == user or self.agent_set.filter(person__user=user, **kwargs).exists()

    def viewable_by(self, user):
        return self.person.user == user or self.agent_set.filter(person__user=user).exists()

    def ordered_pieces(self):
        return self.piece_set.order_by('pieceid')

    def agent_names(self):
        return [agent.person.display_name for agent in self.agent_set.prefetch_related('person').all()]

    def save(self, **kwargs):
        if self.artistid is None:
            try:
                highest_idd_artist = Artist.objects.order_by('-artistid')[0]
                self.artistid = highest_idd_artist.artistid + 1
            except IndexError:
                self.artistid = 1
        super(Artist, self).save(**kwargs)

    @staticmethod
    def apply_space_fees(artists):
        Payment.objects.filter(
            payment_type_id=settings.ARTSHOW_SPACE_FEE_PK,
            artist__in=artists).delete()

        artist_map = {}

        def add_location(artist_id, location):
            size = Decimal(0.5 if location.space_is_split or location.half_space else 1.0)
            artist_spaces = artist_map.setdefault(artist_id, {})
            artist_space = artist_spaces.setdefault(location.type.shortname, {
                'cost': Decimal(0),
                'allocated': Decimal(0)
            })
            artist_space['cost'] += size * location.type.price
            artist_space['allocated'] += size

        for location in Location.objects.filter(artist_1__in=artists).select_related('type'):
            add_location(location.artist_1_id, location)

        for location in Location.objects.filter(artist_2__in=artists).select_related('type'):
            add_location(location.artist_2_id, location)

        payments = []
        for (artist_id, artist_spaces) in artist_map.items():
            total = Decimal(0)
            allocated_spaces = []
            for (shortname, data) in artist_spaces.items():
                total += data['cost']
                allocated_spaces.append(shortname + ':' + str(data['allocated']))

            payments.append(
                Payment(artist_id=artist_id, amount=-total,
                        payment_type_id=settings.ARTSHOW_SPACE_FEE_PK,
                        description=', '.join(allocated_spaces),
                        date=timezone.now()))

        Payment.objects.bulk_create(payments)

    @staticmethod
    def apply_winnings_and_commission(artists):
        Payment.objects.filter(
            payment_type_id__in=(settings.ARTSHOW_SALES_PK,
                                 settings.ARTSHOW_COMMISSION_PK),
            artist__in=artists,
        ).delete()

        artists = artists.annotate(
            pieces=Count('piece', distinct=True),
            pieces_with_bids=Count('piece',
                                   distinct=True,
                                   filter=Q(piece__bid__invalid=False)),
        )
        payments = []
        for artist in artists:
            artist.winnings = Piece.objects.filter(artist=artist).annotate(
                top_bid=Max('bid__amount', filter=Q(bid__invalid=False))
            ).aggregate(winnings=Sum('top_bid'))['winnings']

            if artist.winnings is None:
                continue

            if artist.pieces > 0:
                payments.append(
                    Payment(artist=artist, amount=artist.winnings,
                            payment_type_id=settings.ARTSHOW_SALES_PK,
                            description="%d piece%s, %d with bid%s" % (
                                artist.pieces,
                                artist.pieces != 1 and "s" or "",
                                artist.pieces_with_bids,
                                artist.pieces_with_bids != 1 and "s" or ""),
                            date=timezone.now()))

            commission = artist.winnings * Decimal(settings.ARTSHOW_COMMISSION)
            if commission > 0:
                payments.append(
                    Payment(artist=artist, amount=-commission,
                            payment_type_id=settings.ARTSHOW_COMMISSION_PK,
                            description="%s%% of sales" % (
                                Decimal(settings.ARTSHOW_COMMISSION) * 100),
                            date=timezone.now()))

        Payment.objects.bulk_create(payments)

    @staticmethod
    def create_cheques(artists):
        artists = artists.annotate(balance=Sum('payment__amount'))
        for artist in artists:
            if artist.balance and artist.balance > 0:
                chq = ChequePayment(
                    artist=artist,
                    payment_type_id=settings.ARTSHOW_PAYMENT_SENT_PK,
                    amount=-artist.balance,
                    date=timezone.now())
                chq.clean()
                chq.save()

    class Meta:
        permissions = (
            ('is_artshow_staff', 'Can do generic art-show functions.'),
            ('is_artshow_kiosk', 'Can do kiosk functions.'),
        )


class Allocation(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    space = models.ForeignKey(Space, on_delete=models.CASCADE)
    requested = models.DecimalField(max_digits=4, decimal_places=1, validators=[validate_space])
    allocated = models.DecimalField(max_digits=4, decimal_places=1, validators=[validate_space], default=0)

    def clean(self):
        validate_space_increments(self.requested, self.space.allow_half_spaces)
        validate_space_increments(self.allocated, self.space.allow_half_spaces)

    def requested_charge(self):
        return self.requested * self.space.price

    def allocated_charge(self):
        return self.allocated * self.space.price

    def __str__(self):
        return "%s (%s) - %s/%s %s" % (self.artist.artistname(), self.artist.artistid,
                                       self.allocated, self.requested, self.space.name)

    class Meta:
        unique_together = (('artist', 'space'), )


class Bidder (models.Model):
    person = models.OneToOneField(settings.ARTSHOW_PERSON_CLASS,
                                  on_delete=models.CASCADE)

    def name(self):
        return self.person.name
    at_con_contact = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def bidder_ids(self):
        return [b_id.id for b_id in self.bidderid_set.all().order_by('id')]

    def top_bids(self, unsold_only=False):
        results = []
        bids = self.bid_set.filter(invalid=False)
        for b in bids:
            if b.is_top_bid and (not unsold_only or b.piece.status != Piece.StatusSold):
                results.append(b)
        return results

    def get_results(self):
        pieces_won = []
        pieces_not_won = []
        pieces_in_voice_auction = []

        winning_bid_query = Bid.objects.filter(
            piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
        pieces = Piece.objects.filter(bid__bidder=self).annotate(
            top_bidder=Subquery(winning_bid_query.values('bidder')),
            top_bid=Subquery(winning_bid_query.values('amount'))
        ).order_by('artist', 'code').distinct()

        for piece in pieces:
            if piece.status == Piece.StatusInShow and piece.voice_auction:
                pieces_in_voice_auction.append(piece)
            elif piece.status == Piece.StatusWon or piece.status == Piece.StatusSold:
                if piece.top_bidder == self.pk:
                    pieces_won.append(piece)
                else:
                    pieces_not_won.append(piece)

        return pieces_won, pieces_not_won, pieces_in_voice_auction

    def unsold_pieces(self):
        winning_bid_query = Bid.objects.filter(
            piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
        return Piece.objects.filter(
            status=Piece.StatusWon,
            bid__bidder=self
        ).annotate(
            top_bidder=Subquery(winning_bid_query.values('bidder')),
            top_bid=Subquery(winning_bid_query.values('amount'))
        ).filter(top_bidder=self.pk).order_by('artist', 'code').distinct()

    def voice_auction_wins(self, adult):
        winning_bid_query = Bid.objects.filter(
            piece=OuterRef('pk'), invalid=False).order_by('-amount')[:1]
        return Piece.objects.filter(
            status=Piece.StatusWon,
            voice_auction=True,
            adult=adult,
            bid__bidder=self
        ).annotate(
            top_bidder=Subquery(winning_bid_query.values('bidder')),
            top_bid=Subquery(winning_bid_query.values('amount'))
        ).filter(top_bidder=self.pk).order_by('artist', 'code').distinct()

    def __str__(self):
        return "%s (%s)" % (self.person.name, ", ".join(self.bidder_ids()))


class BidderId (models.Model):
    id = models.CharField(max_length=8, primary_key=True)
    bidder = models.ForeignKey(Bidder, null=True, on_delete=models.CASCADE)

    def validate(self):
        try:
            mod11codes.check(str(self.id))
        except mod11codes.CheckDigitError:
            raise ValidationError("Bidder ID is not valid")

    def __str__(self):
        name = self.bidder.person.name if self.bidder else "Unassigned"
        return "BidderId %s (%s)" % (self.id, name)


class Piece (models.Model):

    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    pieceid = models.IntegerField()
    code = models.CharField(max_length=10, editable=False)
    name = models.CharField(max_length=100, verbose_name="title")
    media = models.CharField(max_length=100, blank=True)
    other_artist = models.CharField(
        max_length=100, blank=True,
        help_text="Alternate artist name for this piece")
    condition = models.CharField(
        max_length=100, blank=True,
        help_text="Condition of piece, if not \"perfect\".")
    location = models.CharField(max_length=8, blank=True)
    not_for_sale = models.BooleanField(default=False)
    adult = models.BooleanField(default=False)
    min_bid = models.DecimalField(
        max_digits=5, decimal_places=0, blank=True, null=True)
    buy_now = models.DecimalField(
        max_digits=5, decimal_places=0, blank=True, null=True)
    reproduction_rights_included = models.BooleanField(
        default=False,
        help_text="This sale includes reproduction rights to the piece.")
    voice_auction = models.BooleanField(default=False)
    bidsheet_scanned = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)
    order = models.IntegerField(null=True, blank=True)
    bids_updated = models.DateTimeField(null=True, blank=True, default=None)

    StatusNotInShow = 0
    StatusInShow = 1
    StatusWon = 2
    StatusSold = 3
    StatusReturned = 4
    StatusNotInShowLocked = 5

    STATUS_CHOICES = [
        (StatusNotInShow, 'Not In Show'),
        (StatusNotInShowLocked, 'Not In Show, Locked'),
        (StatusInShow, 'In Show'),
        (StatusWon, 'Won'),
        (StatusSold, 'Sold'),
        (StatusReturned, 'Returned'),
    ]
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=StatusNotInShow)

    PrintingNotPrinted = 0
    PrintingToBePrinted = 1
    PrintingPrinted = 2
    PRINTING_CHOICES = [
        (PrintingNotPrinted, 'Not Printed'),
        (PrintingToBePrinted, 'To Be Printed'),
        (PrintingPrinted, 'Printed'),
    ]

    bid_sheet_printing = models.IntegerField(choices=PRINTING_CHOICES, default=PrintingNotPrinted)
    control_form_printing = models.IntegerField(choices=PRINTING_CHOICES, default=PrintingNotPrinted)

    def artistname(self):
        return self.other_artist or self.artist.artistname()

    def top_bid(self):
        return self.bid_set.exclude(invalid=True).order_by('-amount')[0:1].get()

    def is_artist_editable(self):
        return self.status == Piece.StatusNotInShow

    def save(self, *args, **kwargs):
        self.code = "%s-%s" % (self.artist.artistid, self.pieceid)
        if self.location and self.status == Piece.StatusNotInShow:
            self.status = Piece.StatusInShow
        if not self.location and self.status == Piece.StatusInShow:
            self.status = Piece.StatusNotInShow
        super(Piece, self).save(*args, **kwargs)

    def __str__(self):
        return "%s - \"%s\" by %s" % (self.code, self.name, self.artistname())

    def clean(self):
        if self.pieceid is not None and self.pieceid <= 0:
            raise ValidationError("Piece IDs must be greater than 0")
        if self.pieceid is not None and self.pieceid > settings.ARTSHOW_MAX_PIECE_ID:
            raise ValidationError("Piece IDs must not be greater than " + str(settings.ARTSHOW_MAX_PIECE_ID))
        if self.min_bid is not None and self.min_bid <= 0:
            raise ValidationError("Minimum Bid if specified must be greater than zero")
        if self.buy_now is not None and self.buy_now <= 0:
            raise ValidationError("Buy Now if specified must be greater than zero")
        if self.not_for_sale and self.min_bid:
            raise ValidationError("A Piece cannot be Not For Sale and have a Minimum Bid")
        if self.not_for_sale and self.buy_now:
            raise ValidationError("A Piece cannot be Not For Sale and have a Buy Now Price")
        if not self.not_for_sale and not self.min_bid:
            raise ValidationError("A Piece must either be Not For Sale or have a Minimum Bid")
        if self.min_bid and self.buy_now and self.min_bid >= self.buy_now:
            raise ValidationError("Buy Now must be empty, or greater than Minimum Bid")

    def apply_won_status(self):
        if self.status == Piece.StatusInShow:
            bid_count = self.bid_set.exclude(invalid=True).count()
            if bid_count > 0:
                self.voice_auction = bid_count >= 6
                if not self.voice_auction:
                    self.status = Piece.StatusWon
                self.save()

    class Meta:
        unique_together = (
            ('artist', 'pieceid'),
        )


class Product (models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    productid = models.IntegerField()
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=8, blank=True)
    adult = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def artistname(self):
        return self.artist.artistname()

    def __str__(self):
        return "A%sR%s - %s by %s (%s)" % (self.artist.artistid, self.productid,
                                           self.name, self.artistname(), self.artist.artistid)


class Bid (models.Model):
    bidder = models.ForeignKey(Bidder, on_delete=models.CASCADE)
    bidderid = models.ForeignKey(BidderId, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=5, decimal_places=0)
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE)
    buy_now_bid = models.BooleanField(default=False)
    invalid = models.BooleanField(default=False)

    def _is_top_bid(self):
        return self.piece.top_bid() == self
    is_top_bid = property(_is_top_bid)

    def __str__(self):
        return "%s (%s) %s $%s on %s" % (self.bidder.name(), self.bidderid,
                                         "INVALID BID" if self.invalid else "bid", self.amount, self.piece)

    class Meta:
        unique_together = (('piece', 'amount', 'invalid'), )

    def validate(self):
        # super(Bid,self).validate()
        if self.piece.not_for_sale:
            raise ValidationError("Not For Sale piece cannot have bids placed on it")
        if self.id is None:
            if self.piece.status != Piece.StatusInShow:
                raise ValidationError("New bids cannot be placed on pieces that are not In Show")
            try:
                top_bid = self.piece.top_bid()
                if self.amount <= top_bid.amount:
                    raise ValidationError("New bid must be higher than existing bids")
                if self.piece.buy_now and top_bid.buy_now_bid:
                    raise ValidationError("Cannot bid on piece that has had Buy Now option invoked")
                if self.buy_now_bid:
                    raise ValidationError("Buy Now option not available on piece with bids")
            except Bid.DoesNotExist:
                pass
        if self.buy_now_bid:
            if not self.piece.buy_now:
                raise ValidationError("Buy Now option not available on this piece")
            if self.amount < self.piece.buy_now:
                raise ValidationError("Buy Now bid cannot be less than Buy Now price")
        if self.amount < self.piece.min_bid:
            raise ValidationError("Bid cannot be less than Min Bid")

    def save(self, **kwargs):
        try:
            self.bidderid
        except BidderId.DoesNotExist:
            self.bidderid = self.bidder.bidderid_set.first()
        super(Bid, self).save(**kwargs)


class EmailTemplate (models.Model):
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    template = models.TextField()
    template.help_text = "Begin a line with \".\" to enable word-wrap. " \
        "Use Django template language. " \
        "Available variables: artist, pieces_in_show, payments, signature, artshow_settings. "

    def __str__(self):
        return self.name


class EmailSignature (models.Model):
    name = models.CharField(max_length=100)
    signature = models.TextField()

    def __str__(self):
        return self.name


class PaymentType (models.Model):
    name = models.CharField(max_length=40)

    def __str__(self):
        return self.name


class Payment (models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    payment_type = models.ForeignKey(PaymentType, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return "%s (%s) %s %s" % (self.artist.artistname(), self.artist.artistid, self.amount, self.date)


class ChequePayment (Payment):
    number = models.CharField(max_length=10, blank=True)
    payee = models.CharField(max_length=100, blank=True)

    def clean(self):
        if not self.payee:
            self.payee = self.artist.chequename()
        if self.amount >= 0:
            raise ValidationError("Cheque amounts are a payment outbound and must be negative")
        self.payment_type_id = settings.ARTSHOW_PAYMENT_SENT_PK
        self.description = "Cheque %s Payee %s" % (self.number and "#" + self.number or "pending number", self.payee)

    @property
    def amount_string(self):
        return str(-self.amount)

    @property
    def amount_words(self):
        amount = -self.amount
        dollars = int(amount)
        cents = int((amount - dollars) * 100 + Decimal("0.5"))
        return '%s dollars and %s cents' % (num2words(dollars), num2words(cents))


class SquarePayment (Payment):
    payment_link_id = models.CharField(max_length=192)
    payment_link_url = models.CharField(max_length=255)
    order_id = models.CharField(max_length=192)
    payment_id = models.CharField(max_length=192, blank=True)


class Invoice (models.Model):
    payer = models.ForeignKey(Bidder, on_delete=models.CASCADE)
    tax_paid = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)

    def total_paid(self):
        return self.invoicepayment_set.filter(complete=True).aggregate(sum=Sum('amount'))['sum'] or Decimal('0.0')

    def item_total(self):
        return self.invoiceitem_set.aggregate(sum=Sum('price'))['sum'] or Decimal('0.0')

    def item_and_tax_total(self):
        return self.item_total() + (self.tax_paid or 0)

    def payment_remaining(self):
        return self.item_and_tax_total() - self.total_paid()

    def invoiceitems(self):
        return self.invoiceitem_set.order_by('piece__location', 'piece')

    paid_date = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)

    def __str__(self):
        return "Invoice %d for %s" % (self.id, self.payer)

    def get_absolute_url(self):
        return reverse('artshow-cashier-invoice', args=[str(self.id)])


class InvoicePayment(models.Model):
    # The cashier code expects this ordering and numbering to special-case each of the payment
    # types.
    class PaymentMethod(models.IntegerChoices):
        NOT_PAID = 0, "Not Paid"
        CASH = 1, "Cash"
        CHECK = 2, "Check"
        MANUAL_CARD = 3, "Card"  # Manually processed credit card transaction.
        OTHER = 4, "Other"
        SQUARE_CARD = 5, "Card"  # Credit card captured by Square Terminal.

    complete = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    payment_method = models.IntegerField(choices=PaymentMethod.choices,
                                         default=PaymentMethod.NOT_PAID)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    notes = models.CharField(max_length=100, blank=True)


class SquareInvoicePayment (InvoicePayment):
    checkout_id = models.CharField(max_length=255)
    payment_ids = models.TextField(blank=True)


class InvoiceItem (models.Model):
    piece = models.OneToOneField(Piece, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=7, decimal_places=2)

    def __str__(self):
        return "%s for $%s" % (self.invoice, self.price)


class BatchScan (models.Model):
    BATCHTYPES = [
        (0, "Unknown"),
        (1, "Locations"),
        (2, "Intermediate Bids"),
        (3, "Final Bids"),
        (4, "Bidder ID Allocation"),
    ]
    batchtype = models.IntegerField(choices=BATCHTYPES, default=0)
    data = models.TextField()
    original_data = models.TextField(blank=True)
    date_scanned = models.DateTimeField()
    processed = models.BooleanField(default=False)
    processing_log = models.TextField(blank=True)

    def __str__(self):
        return "BatchScan %s" % self.id


class Event (models.Model):
    name = models.CharField(max_length=100)
    occurred = models.BooleanField(default=False)
    auto_occur = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name


class Task (models.Model):
    summary = models.CharField(max_length=100)
    detail = models.TextField(blank=True)
    time_entered = models.DateTimeField()
    due_at = models.ForeignKey(Event, on_delete=models.CASCADE)
    actor = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    done = models.BooleanField(default=False)

    def __str__(self):
        return self.summary


class Agent(models.Model):
    person = models.ForeignKey(settings.ARTSHOW_PERSON_CLASS,
                               on_delete=models.CASCADE,
                               related_name="agent_for")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    can_edit_spaces = models.BooleanField(default=False, help_text="Person is allowed to reserve or cancel spaces")
    can_edit_pieces = models.BooleanField(default=False,
                                          help_text="Person is allowed to add, delete or change piece details")
    can_deliver_pieces = models.BooleanField(default=False, help_text="Person is allowed to deliver pieces to the show")
    can_retrieve_pieces = models.BooleanField(default=False,
                                              help_text="Person is allowed to retrieve pieces from the show")
    can_arbitrate = models.BooleanField(default=False,
                                        help_text="Person is allowed to make executive decisions regarding pieces")


class SquareTerminal(models.Model):
    device_id = models.CharField(max_length=128)
    code = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    checkout_id = models.CharField(max_length=255, blank=True)


class SquareWebhook(models.Model):
    timestamp = models.DateTimeField()
    body = models.JSONField()


class TelegramWebhook(models.Model):
    timestamp = models.DateTimeField()
    body = models.JSONField()


class BulkMessagingTask(models.Model):
    name = models.CharField(max_length=100)
    message_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)

    @property
    def percentage(self):
        return float(self.sent_count) / self.message_count * 100

    @property
    def remaining(self):
        return self.message_count - self.sent_count
