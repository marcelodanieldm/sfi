from unittest.mock import Mock, patch

from django.test import RequestFactory, TestCase, override_settings

from core.controllers.mentor_ia_controller import _start_stripe_checkout, mentor_ia_checkout_success
from core.controllers.unified_webhook_controller import _upsert_stripe_sub, sync_mp_subscription
from core.models import MentorIASubscription, User


class MentorIASubscriptionFlowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='tester',
			email='tester@example.com',
			password='Password123!',
		)

	def test_stripe_checkout_redirects_active_subscriber_to_hub(self):
		MentorIASubscription.objects.create(
			user=self.user,
			payment_provider='stripe',
			stripe_customer_id='cus_123',
			stripe_subscription_id='sub_123',
			status='active',
		)
		request = RequestFactory().get('/mentoria/checkout/monthly/start/')
		request.user = self.user

		response = _start_stripe_checkout(request, 'monthly')

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, '/practica/')

	@patch('core.services.email_service.send_subscription_confirmation_email')
	def test_stripe_webhook_links_checkout_subscription_by_user_id(self, mock_email):
		stripe_sub = {
			'id': 'sub_new',
			'customer': 'cus_new',
			'status': 'active',
			'current_period_end': None,
			'metadata': {},
		}

		_upsert_stripe_sub(stripe_sub, user_id=str(self.user.id), billing_cycle='bimonthly')

		sub = self.user.mentoria_subscription
		self.assertEqual(sub.payment_provider, 'stripe')
		self.assertEqual(sub.billing_cycle, 'bimonthly')
		self.assertEqual(sub.stripe_subscription_id, 'sub_new')
		self.assertEqual(sub.stripe_customer_id, 'cus_new')
		self.assertEqual(sub.status, 'active')
		mock_email.assert_called_once_with(self.user, 'stripe', None)

	@patch('stripe.checkout.Session.retrieve')
	def test_stripe_success_ignores_session_from_another_user(self, mock_retrieve):
		other_user = User.objects.create_user(
			username='other',
			email='other@example.com',
			password='Password123!',
		)
		mock_retrieve.return_value = Mock(
			metadata={'user_id': str(other_user.id), 'billing_cycle': 'monthly'},
			customer=Mock(id='cus_other', email=other_user.email),
			customer_email=other_user.email,
			subscription=Mock(id='sub_other', status='active', current_period_end=None),
		)
		request = RequestFactory().get('/mentoria/checkout/success/?session_id=cs_other')
		request.user = self.user

		response = mentor_ia_checkout_success(request)

		self.assertEqual(response.status_code, 302)
		self.assertFalse(MentorIASubscription.objects.filter(user=self.user).exists())

	@override_settings(MP_ACCESS_TOKEN='TEST-token')
	@patch('core.services.email_service.send_subscription_confirmation_email')
	@patch('mercadopago.SDK')
	def test_mp_sync_notifies_when_existing_subscription_becomes_active(self, mock_sdk, mock_email):
		MentorIASubscription.objects.create(
			user=self.user,
			payment_provider='mercadopago',
			billing_cycle='monthly',
			mp_preapproval_id='preapproval_123',
			status='inactive',
		)
		sdk = Mock()
		sdk.preapproval.return_value.get.return_value = {
			'status': 200,
			'response': {
				'id': 'preapproval_123',
				'status': 'authorized',
				'payer_id': 'payer_123',
				'payer_email': self.user.email,
				'external_reference': f'{self.user.id}:monthly',
				'next_payment_date': None,
			},
		}
		mock_sdk.return_value = sdk

		sync_mp_subscription('preapproval_123')

		sub = MentorIASubscription.objects.get(user=self.user)
		self.assertEqual(sub.status, 'active')
		self.assertEqual(sub.mp_payer_id, 'payer_123')
		mock_email.assert_called_once_with(self.user, 'mercadopago', None)
