import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, ApplicationFactory, FlashcardFactory
from .test_base_ui import UITestBase
from django.utils import timezone
from datetime import timedelta

@pytest.mark.playwright
class TestFlashcardUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self

    def test_start_review_and_side_configuration(self):
        # Create a user and application
        user = UserFactory()
        application = ApplicationFactory(owner=user)
        
        # Create a flashcard that's due for review on the back side only
        now = timezone.now()
        flashcard = FlashcardFactory(
            user=user,
            front_last_review=now,  # Front reviewed now (not due)
            back_last_review=now - timedelta(days=2)  # Back reviewed 2 days ago (due)
        )
        flashcard.applications.add(application)
        
        # Setup the user session and navigate to the application detail page
        self.setup_user_session(self.page, user)
        self.page.goto(f"{self.live_server.url}{reverse('main:application_detail', kwargs={'pk': application.pk})}")
        self.wait_for_page_load(self.page)
        
        # Click the review button
        review_button = self.page.locator("button[data-action='flashcard#fetchNextCard']")
        review_button.click()
        
        # Wait for the ajax request to complete and check for the message
        preview_container = self.page.locator("[data-flashcard-target='previewContainer']")
        preview_container.wait_for()
        
        # Since we're configured to only show front reviews, we should see "Nothing due for review"
        no_review_message = self.page.locator("text='No cards due for review!'")
        assert no_review_message.is_visible(), "Expected 'No cards due for review!' message when only back side is due"

        