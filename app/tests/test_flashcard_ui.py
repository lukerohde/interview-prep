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

    def test_review_flashcard_easy_assessment(self):
        # Create a user and application
        user = UserFactory()
        application = ApplicationFactory(owner=user)
        
        # Create multiple flashcards with different review times
        now = timezone.now()
        
        # Create our target card first (older creation time)
        target_card = FlashcardFactory(
            user=user,
            front='Target Question',
            back='Target Answer',
            front_last_review=now - timedelta(days=2),  # Reviewed 2 days ago
            front_interval=1  # Make it due for review
        )
        target_card.applications.add(application)
        
        # Create some newer cards that were reviewed recently (should appear at top initially)
        recent_cards = []
        for i in range(3):
            card = FlashcardFactory(
                user=user,
                front=f'Recent Question {i}',
                back=f'Recent Answer {i}',
                front_last_review=now - timedelta(hours=i),  # Reviewed within last few hours
                front_interval=60 * 24  # 24 hour interval, so not due yet
            )
            card.applications.add(application)
            recent_cards.append(card)
        
        # Setup the user session and navigate to the application detail page
        self.setup_user_session(self.page, user)
        self.page.goto(f"{self.live_server.url}{reverse('main:application_detail', kwargs={'pk': application.pk})}")
        self.wait_for_page_load(self.page)
        
        # Click the review button
        review_button = self.page.locator("button[data-action='flashcard#fetchNextCard']")
        review_button.click()
        
        # Wait for the card to appear
        review_card = self.page.locator(".review-card")
        review_card.wait_for(state='visible')
        
        # Verify target card is not at the top initially
        first_card_id = self.page.locator(".flashcard-preview").first.get_attribute("data-flashcard-id")
        assert first_card_id != str(target_card.id), "Target card should not be at top initially"

        # Click the easy button
        easy_button = self.page.locator("button[data-action='flashcard#handleSelfAssessment'][data-status='easy']")
        easy_button.click()

         # After clicking easy, verify target card moves to top
        first_preview_card = self.page.locator(".flashcard-preview").first
        first_preview_card.wait_for()
        assert first_preview_card.get_attribute("data-flashcard-id") == str(target_card.id), "Target card should move to top after marking as easy"

        
       
    def test_edit_flashcard_notes(self):
        # Create a user and application
        user = UserFactory()
        application = ApplicationFactory(owner=user)
        
        # Create a flashcard with some initial notes
        flashcard = FlashcardFactory(
            user=user,
            front='What is dependency injection?',
            back='A design pattern where dependencies are passed in rather than created internally',
            front_notes='Remember to mention IoC containers',
            back_notes='Good to mention Spring Framework as an example'
        )
        flashcard.applications.add(application)
        
        # Setup the user session and navigate to the application detail page
        self.setup_user_session(self.page, user)
        self.page.goto(f"{self.live_server.url}{reverse('main:application_detail', kwargs={'pk': application.pk})}")
        self.wait_for_page_load(self.page)
        
        # Click the edit button on the flashcard
        edit_button = self.page.locator(f"[data-flashcard-id='{flashcard.id}'] button[data-action='flashcard#editCard']")
        edit_button.click()
        
        # Wait for the modal to appear
        modal = self.page.locator('#editFlashcardModal')
        modal.wait_for(state='visible')
        
        # Verify the notes are loaded correctly
        front_notes = self.page.locator('#editFlashcardFrontNotes')
        back_notes = self.page.locator('#editFlashcardBackNotes')
        assert front_notes.input_value() == 'Remember to mention IoC containers'
        assert back_notes.input_value() == 'Good to mention Spring Framework as an example'
        
        # Update the notes
        front_notes.fill('Remember IoC containers and mention constructor injection')
        back_notes.fill('Use Spring and ASP.NET Core as examples')
        
        # Save the changes
        save_button = self.page.locator("button[data-action='flashcard#saveEdit']")
        save_button.click()
        
        # Wait for the save to complete
        self.page.wait_for_timeout(500)  # Wait for any animations
        
        # Verify the card in the UI has the updated notes (in data attributes)
        updated_card = self.page.locator(f"[data-flashcard-id='{flashcard.id}']")
        assert updated_card.get_attribute('data-flashcard-front-notes-value') == 'Remember IoC containers and mention constructor injection'
        assert updated_card.get_attribute('data-flashcard-back-notes-value') == 'Use Spring and ASP.NET Core as examples'
        
        # Verify the database was updated
        flashcard.refresh_from_db()
        assert flashcard.front_notes == 'Remember IoC containers and mention constructor injection'
        assert flashcard.back_notes == 'Use Spring and ASP.NET Core as examples'

    def test_edit_flashcard_categories(self):
        # Create a user and application
        user = UserFactory()
        application = ApplicationFactory(owner=user)
        
        # Create a flashcard with some initial tags
        flashcard = FlashcardFactory(
            user=user,
            front="Initial front",
            back="Initial back",
            tags=["python", "django"]
        )
        flashcard.applications.add(application)
        
        # Setup the user session and navigate to the application detail page
        self.setup_user_session(self.page, user)
        self.page.goto(f"{self.live_server.url}{reverse('main:application_detail', kwargs={'pk': application.pk})}")
        self.wait_for_page_load(self.page)
        
        # Find and click the edit button on the flashcard
        edit_button = self.page.locator(".flashcard-preview button[data-action='flashcard#editCard']")
        edit_button.click()
        
        # Get the card ID we're editing
        card_id = self.page.locator(".flashcard-preview").get_attribute("data-flashcard-id")
        
        # Wait for modal to be visible and form elements to be loaded
        modal = self.page.locator("#editFlashcardModal")
        modal.wait_for(state="visible")
        
        # Fill in the form
        front_textarea = self.page.locator("#editFlashcardFront")
        back_textarea = self.page.locator("#editFlashcardBack")
        tags_input = self.page.locator("#editFlashcardTags")
        
        # Verify initial values
        assert front_textarea.input_value() == "Initial front"
        assert back_textarea.input_value() == "Initial back"
        assert tags_input.input_value() == "python,django"
        
        # Update the values
        front_textarea.fill("Updated front")
        back_textarea.fill("Updated back")
        tags_input.fill("python,algorithms,data-structures")
        
        # Click save and wait for modal to be hidden (indicating successful save)
        save_button = self.page.locator("button[data-action='flashcard#saveEdit']")
        save_button.click()
        modal.wait_for(state="hidden")
        
        # Wait for the updated content to appear
        card_selector = f".flashcard-preview[data-flashcard-id='{card_id}'] .flashcard-content div:text-is('Updated front')"
        self.page.wait_for_selector(card_selector)
        
        # Now verify all the updates
        updated_card = self.page.locator(f".flashcard-preview[data-flashcard-id='{card_id}']")
        assert updated_card.locator(".flashcard-content .flashcard-front div").text_content() == "Updated front"
        assert updated_card.locator(".flashcard-content .flashcard-back div").text_content() == "Updated back"
        
        # Verify all tags are present
        tags = updated_card.locator(".flashcard-tags .badge")
        tag_texts = [tag.text_content() for tag in tags.all()]
        assert set(tag_texts) == {"python", "algorithms", "data-structures"}
        