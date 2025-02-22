# tests/test_example.py
import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, DeckFactory, TutorFactory
from .test_base_ui import UITestBase
import os

@pytest.mark.playwright
class TestHomePageUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self

    def test_home_page_one_tutor_one_deck(self):
        """
        Test that the home page displays the decks of the only tutor.
        """
        user = UserFactory()
        deck = DeckFactory(owner=user)
        self.setup_user_session(self.page, user)

        self.page.goto(f"{self.live_server.url}{reverse('main:home')}")
        self.wait_for_page_load(self.page)
        
        assert self.page.title() == 'FlashSpeak'
        name = self.page.locator("h1.display-6")
        assert name.is_visible()
        assert name.text_content().strip() == deck.tutor.deck_name
        
        deck_link = self.page.locator(f"text='{deck.name}'")
        assert deck_link.is_visible()

    def test_home_page_two_tutors(self):
        """
        Test that the home page displays the names of the tutors and their decks.
        """ 
        
        user = UserFactory()
        deck = DeckFactory(owner=user)
        deck2 = DeckFactory(owner=user)
        self.setup_user_session(self.page, user)

        self.page.goto(f"{self.live_server.url}{reverse('main:home')}")
        self.wait_for_page_load(self.page)
        
        assert self.page.title() == 'FlashSpeak'
        name = self.page.locator("h1.display-6")
        assert name.is_visible()
        assert name.text_content().strip() == "Tutors"
        
        deck_link = self.page.locator(f"text='{deck.tutor.name}'")
        assert deck_link.is_visible()
        
        deck_link = self.page.locator(f"text='{deck2.tutor.name}'")
        assert deck_link.is_visible()