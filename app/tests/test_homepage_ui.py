# tests/test_example.py
import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, DeckFactory
from .test_base_ui import UITestBase
import os

@pytest.mark.playwright
class TestHomePageUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self

    def test_home_page(self):
        user = UserFactory()
        deck = DeckFactory(owner=user)
        self.setup_user_session(self.page, user)

        self.page.goto(f"{self.live_server.url}{reverse('main:home')}")
        self.wait_for_page_load(self.page)
        
        assert self.page.title() == 'Study Decks'
        name = self.page.locator("h1.display-6")
        assert name.is_visible()
        assert name.text_content().strip() == 'Study Decks'
        
        deck_link = self.page.locator(f"text='{deck.name}'")
        assert deck_link.is_visible()