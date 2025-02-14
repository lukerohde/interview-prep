# tests/test_example.py
import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, ThingFactory
from .test_base_ui import UITestBase
import os

@pytest.mark.playwright
class TestExample(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self

    def test_example(self):
        user = UserFactory()
        thing = ThingFactory()
        self.setup_user_session(self.page, user)

        self.page.goto(f"{self.live_server.url}{reverse('main:thing_list')}")
        self.wait_for_page_load(self.page)
        
        assert self.page.title() == 'Things'
        name = self.page.locator(f"h1:text('Things')")
        assert name.is_visible()
        name = self.page.locator(f"a:href('{reverse('main:thing_detail', thing.pk)}')")
        assert name.is_visible()