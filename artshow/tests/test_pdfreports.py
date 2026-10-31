from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from pdfrw import PdfReader

from .. import pdfreports
from ..models import Artist, Bid, Bidder, BidderId, Invoice, InvoiceItem, InvoicePayment, Piece
from peeps.models import Person


class PDFReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(username='pdf-staff')
        cls.staff.user_permissions.add(Permission.objects.get(codename='is_artshow_staff'))

        artist = Artist.objects.create(
            person=Person.objects.create(name='Alex Artist'),
            publicname='Art & Illustration', artistid=1)
        bidder = Bidder.objects.create(
            person=Person.objects.create(name='Pat Buyer', reg_id='42'))
        bidder_id = BidderId.objects.create(id='0365327', bidder=bidder)
        BidderId.objects.create(id='0019', bidder=bidder)
        losing_bidder = Bidder.objects.create(
            person=Person.objects.create(name='Sam Bidder', reg_id='43'))
        losing_bidder_id = BidderId.objects.create(id='0027', bidder=losing_bidder)

        cls.invoice = Invoice.objects.create(
            payer=bidder, tax_paid=Decimal('6.50'), paid_date=timezone.now(),
            created_by=cls.staff)
        original = Piece.objects.create(
            artist=artist, pieceid=1, name='Sun & Moon <Study>', media='Ink & watercolor',
            min_bid=10, location='B2', status=Piece.StatusSold)
        print_piece = Piece.objects.create(
            artist=artist, pieceid=2, name='Night Sky', media='Print',
            original=False, print_number=2, print_run=20, other_artist='Guest & Co.',
            condition='Small crease <1 inch', min_bid=10, location='A1',
            voice_auction=True, status=Piece.StatusSold)
        Bid.objects.create(bidder=losing_bidder, bidderid=losing_bidder_id,
                           piece=original, amount=10)
        for piece, price in ((original, Decimal('25.00')), (print_piece, Decimal('40.00'))):
            Bid.objects.create(bidder=bidder, bidderid=bidder_id, piece=piece, amount=price)
            InvoiceItem.objects.create(invoice=cls.invoice, piece=piece, price=price)
        InvoicePayment.objects.create(
            invoice=cls.invoice, payment_method=InvoicePayment.PaymentMethod.CASH,
            amount=Decimal('71.50'), complete=True)

    def setUp(self):
        self.client.force_login(self.staff)

    def assert_pdf_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))
        pdf = PdfReader(fdata=response.content)
        self.assertGreater(len(pdf.pages), 0)
        for page in pdf.pages:
            self.assertIsNotNone(page.Contents)

    def test_invoice_pdf(self):
        response = self.client.get(reverse(pdfreports.pdf_invoice, args=[self.invoice.pk]))
        self.assert_pdf_response(response)

    def test_picklist_pdf(self):
        response = self.client.get(reverse(pdfreports.pdf_picklist, args=[self.invoice.pk]))
        self.assert_pdf_response(response)

    def test_winning_bidders_pdf(self):
        response = self.client.get(reverse('artshow-winning-bidders-pdf'))
        self.assert_pdf_response(response)

    def test_bid_entry_by_location_pdf(self):
        response = self.client.get(reverse(pdfreports.bid_entry_by_location))
        self.assert_pdf_response(response)
