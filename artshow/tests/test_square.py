from decimal import Decimal
from unittest import mock

import httpx
from django.conf import settings
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth.models import Permission, User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from square.core.api_error import ApiError
from square.types.delete_payment_link_response import DeletePaymentLinkResponse
from square.types.error import Error

from peeps.models import Person

from .. import square
from ..models import Artist, Payment, PaymentType, SquarePayment


class DeletePaymentLinkTests(TestCase):
    @mock.patch('artshow.square.client')
    def test_delete_payment_link_success(self, mock_client):
        mock_client.return_value.checkout.payment_links.delete.return_value = (
            DeletePaymentLinkResponse(id='LINK1', cancelled_order_id='ORD1')
        )

        self.assertTrue(square.delete_payment_link('LINK1'))
        mock_client.return_value.checkout.payment_links.delete.assert_called_once_with('LINK1')

    @mock.patch('artshow.square.client')
    def test_delete_payment_link_api_error(self, mock_client):
        mock_client.return_value.checkout.payment_links.delete.side_effect = ApiError(
            status_code=404,
            body={
                'errors': [
                    {
                        'category': 'INVALID_REQUEST_ERROR',
                        'code': 'NOT_FOUND',
                        'detail': 'Payment link not found.',
                    }
                ]
            },
        )

        with self.assertLogs('artshow.square', level='ERROR') as logs:
            self.assertFalse(square.delete_payment_link('LINK1'))

        self.assertIn('INVALID_REQUEST_ERROR:NOT_FOUND: Payment link not found.', logs.output[0])

    @mock.patch('artshow.square.client')
    def test_delete_payment_link_response_errors(self, mock_client):
        mock_client.return_value.checkout.payment_links.delete.return_value = (
            DeletePaymentLinkResponse(
                errors=[
                    Error(
                        category='API_ERROR',
                        code='INTERNAL_SERVER_ERROR',
                        detail='Temporary failure.',
                    )
                ]
            )
        )

        with self.assertLogs('artshow.square', level='ERROR') as logs:
            self.assertFalse(square.delete_payment_link('LINK1'))

        self.assertIn('API_ERROR:INTERNAL_SERVER_ERROR: Temporary failure.', logs.output[0])

    @mock.patch('artshow.square.client')
    def test_delete_payment_link_http_error(self, mock_client):
        mock_client.return_value.checkout.payment_links.delete.side_effect = (
            httpx.ConnectError('connection failed')
        )

        with self.assertLogs('artshow.square', level='ERROR'):
            self.assertFalse(square.delete_payment_link('LINK1'))

    @mock.patch('artshow.square.client')
    def test_delete_payment_link_empty_id(self, mock_client):
        with self.assertLogs('artshow.square', level='ERROR'):
            self.assertFalse(square.delete_payment_link(''))

        mock_client.return_value.checkout.payment_links.delete.assert_not_called()


class SquarePaymentAdminActionTests(TestCase):
    fixtures = ['artshowpaymenttypes']

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='password'
        )
        cls.view_only_staff = User.objects.create_user(
            username='viewer', password='password', is_staff=True
        )
        cls.view_only_staff.user_permissions.add(
            Permission.objects.get(codename='view_squarepayment')
        )
        cls.artist = Artist.objects.create(
            person=Person.objects.create(name='Alex Artist'),
            publicname='Alex Art',
            artistid=1,
        )
        cls.pending_type = PaymentType.objects.get(pk=settings.ARTSHOW_PAYMENT_PENDING_PK)
        cls.received_type = PaymentType.objects.get(pk=settings.ARTSHOW_PAYMENT_RECEIVED_PK)
        cls.changelist_url = reverse('admin:artshow_squarepayment_changelist')

    def setUp(self):
        self.client.force_login(self.superuser)

    def create_square_payment(self, payment_type, link_id='LINK1', order_id='ORD1', amount='15.00'):
        return SquarePayment.objects.create(
            artist=self.artist,
            amount=Decimal(amount),
            payment_type=payment_type,
            description='Square payment',
            date=timezone.now().date(),
            payment_link_id=link_id,
            payment_link_url=f'https://square.link/{link_id}',
            order_id=order_id,
        )

    def post_cancel_action(self, payments):
        return self.client.post(
            self.changelist_url,
            {
                'action': 'cancel_pending_payments',
                '_selected_action': [str(p.pk) for p in payments],
            },
            follow=True,
        )

    @mock.patch('artshow.square.client')
    def test_cancel_pending_payment_success(self, mock_client):
        mock_client.return_value.checkout.payment_links.delete.return_value = (
            DeletePaymentLinkResponse(id='LINK_OK', cancelled_order_id='ORD_OK')
        )
        payment = self.create_square_payment(self.pending_type, link_id='LINK_OK', order_id='ORD_OK')

        response = self.post_cancel_action([payment])

        self.assertEqual(response.status_code, 200)
        mock_client.return_value.checkout.payment_links.delete.assert_called_once_with('LINK_OK')
        self.assertFalse(SquarePayment.objects.filter(pk=payment.pk).exists())
        self.assertFalse(Payment.objects.filter(pk=payment.pk).exists())
        self.assertTrue(
            LogEntry.objects.filter(
                user=self.superuser,
                object_id=str(payment.pk),
                action_flag=DELETION,
            ).exists()
        )
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn(f'Cancelled pending payment {payment.id}.', msgs)

    @mock.patch('artshow.square.client')
    def test_cancel_pending_payment_api_failure_keeps_pending(self, mock_client):
        mock_client.return_value.checkout.payment_links.delete.side_effect = ApiError(
            status_code=500,
            body={
                'errors': [
                    {
                        'category': 'API_ERROR',
                        'code': 'INTERNAL_SERVER_ERROR',
                        'detail': 'Square error',
                    }
                ]
            },
        )
        payment = self.create_square_payment(self.pending_type, link_id='LINK_FAIL', order_id='ORD_FAIL')

        with self.assertLogs('artshow.square', level='ERROR'):
            response = self.post_cancel_action([payment])

        self.assertEqual(response.status_code, 200)
        mock_client.return_value.checkout.payment_links.delete.assert_called_once_with('LINK_FAIL')
        payment.refresh_from_db()
        self.assertEqual(payment.payment_type_id, settings.ARTSHOW_PAYMENT_PENDING_PK)
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn(f'Failed to cancel payment {payment.id} with Square.', msgs)

    @mock.patch('artshow.square.client')
    def test_non_pending_payment_is_not_cancelled(self, mock_client):
        payment = self.create_square_payment(self.received_type, link_id='LINK_DONE', order_id='ORD_DONE')

        response = self.post_cancel_action([payment])

        self.assertEqual(response.status_code, 200)
        mock_client.return_value.checkout.payment_links.delete.assert_not_called()
        payment.refresh_from_db()
        self.assertEqual(payment.payment_type_id, settings.ARTSHOW_PAYMENT_RECEIVED_PK)
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn(f'Payment {payment.id} is not pending and cannot be cancelled.', msgs)

    @mock.patch('artshow.square.client')
    def test_mixed_selection(self, mock_client):
        pending_ok = self.create_square_payment(self.pending_type, link_id='LINK_1', order_id='ORD_1')
        pending_fail = self.create_square_payment(self.pending_type, link_id='LINK_2', order_id='ORD_2')
        received = self.create_square_payment(self.received_type, link_id='LINK_3', order_id='ORD_3')

        def delete_side_effect(link_id):
            if link_id == 'LINK_1':
                return DeletePaymentLinkResponse(id='LINK_1', cancelled_order_id='ORD_1')
            raise ApiError(
                status_code=400,
                body={'errors': [{'category': 'INVALID_REQUEST_ERROR', 'code': 'BAD_REQUEST', 'detail': 'bad'}]},
            )

        mock_client.return_value.checkout.payment_links.delete.side_effect = delete_side_effect

        with self.assertLogs('artshow.square', level='ERROR'):
            response = self.post_cancel_action([pending_ok, pending_fail, received])

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            mock_client.return_value.checkout.payment_links.delete.call_args_list,
            [mock.call('LINK_1'), mock.call('LINK_2')],
        )
        self.assertFalse(SquarePayment.objects.filter(pk=pending_ok.pk).exists())
        pending_fail.refresh_from_db()
        self.assertEqual(pending_fail.payment_type_id, settings.ARTSHOW_PAYMENT_PENDING_PK)
        received.refresh_from_db()
        self.assertEqual(received.payment_type_id, settings.ARTSHOW_PAYMENT_RECEIVED_PK)

    @mock.patch('artshow.square.client')
    def test_concurrent_completion_prevents_deletion(self, mock_client):
        payment = self.create_square_payment(self.pending_type, link_id='LINK_RACE', order_id='ORD_RACE')

        def complete_during_delete(link_id):
            SquarePayment.objects.filter(pk=payment.pk).update(
                payment_type_id=settings.ARTSHOW_PAYMENT_RECEIVED_PK,
                payment_id='PAY_123',
            )
            return DeletePaymentLinkResponse(id=link_id, cancelled_order_id='ORD_RACE')

        mock_client.return_value.checkout.payment_links.delete.side_effect = complete_during_delete

        response = self.post_cancel_action([payment])

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.payment_type_id, settings.ARTSHOW_PAYMENT_RECEIVED_PK)
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn(f'Payment {payment.id} is no longer pending.', msgs)

    @mock.patch('artshow.square.client')
    def test_requires_delete_permission(self, mock_client):
        self.client.force_login(self.view_only_staff)
        payment = self.create_square_payment(self.pending_type, link_id='LINK_PERM', order_id='ORD_PERM')

        response = self.post_cancel_action([payment])

        self.assertEqual(response.status_code, 200)
        mock_client.return_value.checkout.payment_links.delete.assert_not_called()
        self.assertTrue(SquarePayment.objects.filter(pk=payment.pk).exists())
