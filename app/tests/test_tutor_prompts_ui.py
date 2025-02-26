import pytest
import yaml
import tempfile
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, TutorFactory
from .test_base_ui import UITestBase
from main.models import TutorPromptOverride

@pytest.mark.playwright
class TestTutorPromptsUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self

    def test_prompt_override_save_and_remove(self):
        """Test saving and removing a prompt override"""
        # Create test config
        config = {
            'url-path': 'test-tutor',
            'prompt-override-whitelist': [
                'prompts.generate_flashcards.system'
            ],
            'prompts': {
                'generate_flashcards': {
                    'system': 'Default system prompt'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            tutor_config = f.name
        # Create test data
        user = UserFactory()
        tutor = TutorFactory(
            url_path='test-tutor',
            config_path=tutor_config
        )
        
        # Setup session and navigate to tutor prompts page
        self.setup_user_session(self.page, user)
        self.page.goto(f"{self.live_server.url}{reverse('main:tutor_prompts', kwargs={'url_path': tutor.url_path})}")
        self.wait_for_page_load(self.page)
        
        # Find and update the system prompt field
        system_prompt = self.page.locator("textarea[data-key='prompts.generate_flashcards.system']")
        system_prompt.click()
        system_prompt.press("Control+A")
        system_prompt.press("Backspace")
        system_prompt.fill("My custom system prompt")
        system_prompt.press("Tab")  # Trigger blur event for auto-save
        
        # Wait for saving indicator to appear and disappear
        saving = self.page.locator(".save-indicator:visible")
        saving.wait_for(state="attached")
        saving.wait_for(state="detached")
        
        # Verify override was saved in database
        override = TutorPromptOverride.objects.get(
            user=user,
            tutor_url_path=tutor.url_path,
            key='prompts.generate_flashcards.system'
        )
        assert override.value == "My custom system prompt"
        
        # Clear the field to remove the override
        system_prompt.fill("")
        system_prompt.press("Tab")
        
        # Wait for saving indicator
        saving = self.page.locator(".save-indicator:visible")
        saving.wait_for(state="attached")
        saving.wait_for(state="detached")
        
        # Verify override was removed from database
        assert not TutorPromptOverride.objects.filter(
            user=user,
            tutor_url_path=tutor.url_path,
            key='prompts.generate_flashcards.system'
        ).exists()

    def tearDown(self):
        """Clean up any temporary files"""
        import os
        temp_dir = tempfile.gettempdir()
        for file in os.listdir(temp_dir):
            if file.endswith('.yaml'):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except:
                    pass
