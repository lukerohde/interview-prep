import pytest
import yaml
import tempfile
import os
from django.test import Client
from django.urls import reverse
from .factories import UserFactory, TutorFactory
from main.models import TutorPromptOverride, Tutor

pytestmark = pytest.mark.django_db

@pytest.fixture
def tutor_config():
    config = {
        'url-path': 'test-tutor',
        'prompt-override-whitelist': [
            'prompts.generate_flashcards.system',
            'prompts.generate_flashcards.user'
        ],
        'prompts': {
            'generate_flashcards': {
                'system': 'You are a helpful flashcard generator',
                'user': 'Create flashcards from: ${content}'
            },
            'voice_session': {
                'system': 'You are a voice tutor',
                'user': 'Help with: ${topic}'
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        return f.name

@pytest.fixture
def tutor(tutor_config):
    tutor = TutorFactory(
        url_path='test-tutor',
        config_path=tutor_config
    )
    return tutor

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client

def test_prompt_whitelist_respected(tutor, user):
    """Test that only whitelisted prompts are shown to users"""
    # Create both whitelisted and non-whitelisted overrides
    overrides = [
        ('prompts.generate_flashcards.system', 'Custom system prompt'),  # whitelisted
        ('prompts.voice_session.system', 'Custom voice prompt'),  # not whitelisted
    ]
    
    for key, value in overrides:
        TutorPromptOverride.objects.create(
            user=user,
            tutor_url_path=tutor.url_path,
            key=key,
            value=value
        )
    
    # Get the config and check whitelist
    config = tutor.get_config()
    whitelist = config.get('prompt-override-whitelist', [])
    assert 'prompts.generate_flashcards.system' in whitelist
    assert 'prompts.voice_session.system' not in whitelist

def test_non_whitelisted_overrides_not_applied(tutor, user):
    """Test that non-whitelisted overrides are not applied even if they exist"""
    original_voice_prompt = tutor.get_config()['prompts']['voice_session']['system']
    
    # Create a non-whitelisted override
    non_whitelisted = TutorPromptOverride.objects.create(
        user=user,
        tutor_url_path=tutor.url_path,
        key='prompts.voice_session.system',
        value='Custom voice prompt'
    )
    
    # Create a whitelisted override
    whitelisted = TutorPromptOverride.objects.create(
        user=user,
        tutor_url_path=tutor.url_path,
        key='prompts.generate_flashcards.system',
        value='Custom system prompt'
    )
    
    # Get config and verify:
    # 1. Whitelisted override is applied
    # 2. Non-whitelisted override is NOT applied (original value preserved)
    config = tutor.get_config(user)
    assert config['prompts']['voice_session']['system'] == original_voice_prompt, \
        'Non-whitelisted override should not be applied'
    assert config['prompts']['generate_flashcards']['system'] == 'Custom system prompt', \
        'Whitelisted override should be applied'

def teardown_module(module):
    """Clean up any temporary files created during testing"""
    # Clean up any .yaml files in the temp directory
    temp_dir = tempfile.gettempdir()
    for file in os.listdir(temp_dir):
        if file.endswith('.yaml'):
            try:
                os.remove(os.path.join(temp_dir, file))
            except:
                pass
