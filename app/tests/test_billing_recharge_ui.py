import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory
from .test_base_ui import UITestBase
from billing.models import BillingProfile

@pytest.mark.playwright
class TestBillingRechargeUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    def test_recharge_page_basic_elements(self, mock_payment_intent, mock_customer):
        """
        Test that the recharge page shows basic elements and form structure.
        """
        # Mock Stripe responses
        mock_customer.return_value = type('Customer', (), {'id': 'cus_test'})()
        mock_payment_intent.return_value = type('PaymentIntent', (), {
            'id': 'pi_test',
            'client_secret': 'pi_test_secret',
            'status': 'requires_payment_method'
        })()
        
        user = UserFactory()
        billing_profile = BillingProfile.objects.get(user=user)
        billing_profile.stripe_payment_method_id = 'pm_test_123'
        billing_profile.save()
        
        self.setup_user_session(self.page, user)
        self.page.goto(f"{self.live_server.url}{reverse('billing:recharge_credits')}")
        self.wait_for_page_load(self.page)
        
        # Check page title and heading
        assert "Recharge Credits" in self.page.title()
        heading = self.page.locator(".card-title")
        assert heading.is_visible()
        assert "Recharge Credits" in heading.text_content()
        
        # Check recharge form
        form = self.page.locator("form")
        assert form.is_visible()
        
        # Check amount display
        amount_display = self.page.locator(".form-control-static h3")
        assert amount_display.is_visible()
        
        # Check payment form area exists (initially hidden)
        payment_area = self.page.locator("[data-recharge-target='payment']")
        assert payment_area.count() > 0
        
        # Check submit button
        submit_button = self.page.locator("[data-recharge-target='submit']")
        assert submit_button.is_visible()
        assert "Pay $" in submit_button.text_content()
        
        # Check cancel button
        cancel_button = self.page.locator("[data-recharge-target='cancel']")
        assert cancel_button.is_visible()
