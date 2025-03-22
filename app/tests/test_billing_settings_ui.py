import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory
from .test_base_ui import UITestBase
from billing.models import BillingProfile

@pytest.mark.playwright
class TestBillingSettingsUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self
    
    @patch('stripe.Customer.create')
    @patch('stripe.SetupIntent.create')
    def test_settings_page_basic_elements(self, mock_setup_intent, mock_customer):
        """
        Test that the settings page shows basic elements and form structure.
        """
        # Mock Stripe responses
        mock_customer.return_value.id = 'cus_test'
        mock_setup_intent.return_value.client_secret = 'seti_test'
        
        user = UserFactory()
        self.setup_user_session(self.page, user)
        
        self.page.goto(f"{self.live_server.url}{reverse('billing:billing_settings')}")
        self.wait_for_page_load(self.page)
        
        # Check page title and heading
        assert "Billing Settings" in self.page.title()
        heading = self.page.locator(".card-title")
        assert heading.is_visible()
        assert "Billing Settings" in heading.text_content()
        
        # Check auto-recharge form exists
        form = self.page.locator("form")
        assert form.is_visible()
        
        # Check basic form elements
        auto_recharge_toggle = self.page.locator("#id_auto_recharge_enabled")
        assert auto_recharge_toggle.is_visible()
        
        amount_field = self.page.locator("#id_auto_recharge_amount")
        assert amount_field.is_visible()
        
        # Check save button
        save_button = self.page.locator("button[type='submit']")
        assert save_button.is_visible()
