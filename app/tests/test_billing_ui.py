# import pytest
# import json
# from django.urls import reverse
# from django.contrib.staticfiles.testing import StaticLiveServerTestCase
# from .factories import UserFactory, DeckFactory
# from .factories_billing import BillingProfileFactory
# from .test_base_ui import UITestBase
# from decimal import Decimal
# from billing.models import BillingProfile, BillingSettingItem, BillingSettings

# @pytest.mark.playwright
# class TestBillingUI(UITestBase, StaticLiveServerTestCase):
#     @pytest.fixture(autouse=True)
#     def setup_test(self, page, live_server):
#         self.page = page
#         self.live_server = live_server
        
#         # Create a user with a starting balance
#         self.user = UserFactory()
#         self.billing_profile = self.user.billing_profile
#         self.billing_profile.add_credits(Decimal('10.00'), transaction_type='test')
        
#         # Create a deck for testing
#         self.deck = DeckFactory(owner=self.user)
        
#         # Set up the user session
#         self.setup_user_session(self.page, self.user)
#         return self

#     def test_voice_chat_token_usage_and_balance(self):
#         # Navigate to the deck detail page
#         self.page.goto(f"{self.live_server.url}{reverse('main:deck_detail', kwargs={'pk': self.deck.pk, 'url_path': self.deck.tutor.url_path})}")
#         self.wait_for_page_load(self.page)
        

        
#         # Verify initial balance is displayed correctly
#         balance_display = self.page.locator("[data-voice-chat-target='balance']")
#         balance_display.wait_for()
#         assert balance_display.inner_text() == "$10.00"
        
#         # Verify initial cost is zero
#         cost_display = self.page.locator("[data-voice-chat-target='cost']")
#         cost_display.wait_for()
#         assert cost_display.inner_text() == "$0.00"
        
#         # Simulate a voice chat response.done event with token usage
#         # Simulate a WebRTC data channel message
#         self.page.evaluate("""
#         () => {
#             const element = document.querySelector('[data-controller="voice-chat"]')
#             if (!element) throw new Error('Voice chat controller not found')
            
#             // Create a custom event that will trigger the "message" action
#             const event = new CustomEvent('message', {
#                 detail: {
#                     data: JSON.stringify({
#                         type: 'response.done',
#                         response: {
#                             usage: {
#                                 input_token_details: {
#                                     audio_tokens: 100,
#                                     text_tokens: 50,
#                                     cached_tokens: 25
#                                 },
#                                 output_tokens: 200
#                             }
#                         }
#                     })
#                 }
#             })
            
#             // Dispatch to the element
#             element.dispatchEvent(event)
#         }
#         """)
        
#         # Wait for balance to update from $10.00
#         balance_display = self.page.locator("[data-voice-chat-target='balance']")
#         balance_display.wait_for(state="visible")
        
#         # Get the new balance
#         self.billing_profile.refresh_from_db()
#         expected_balance = f"${self.billing_profile.balance:.2f}"
#         assert balance_display.inner_text() == expected_balance, f"Balance should be {expected_balance}, got {balance_display.inner_text()}"
        
#         # Reload page and verify balance persists
#         self.page.reload()
#         self.wait_for_page_load(self.page)
        
#         # Check balance persists and cost resets
#         balance_display = self.page.locator("[data-voice-chat-target='balance']")
#         cost_display = self.page.locator("[data-voice-chat-target='cost']")
        
#         balance_display.wait_for(state="visible")
#         cost_display.wait_for(state="visible")
        
#         assert balance_display.inner_text() == expected_balance, f"Balance should be {expected_balance} after reload"
#         assert cost_display.inner_text() == "$0.00", "Cost should reset after reload"
