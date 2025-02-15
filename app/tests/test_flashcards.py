import pytest
from django.urls import reverse
from django.test import Client
from .factories import UserFactory, FlashcardFactory
from main.models import FlashCard, User
import json

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def clean_database():
    """Clean up the database before each test."""
    FlashCard.objects.all().delete()
    User.objects.all().delete()

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client

def test_flashcard_update(authenticated_client, user):
    # Create a flashcard
    flashcard = FlashcardFactory(user=user)
    
    # Prepare update data
    update_data = {
        'front': 'Updated question',
        'back': 'Updated answer',
        'tags': ['updated', 'test']
    }
    
    # Make the update request
    url = f'/api/flashcards/{flashcard.id}/'
    response = authenticated_client.put(
        url,
        data=json.dumps(update_data),
        content_type='application/json'
    )
    
    # Check response
    assert response.status_code == 200
    response_data = response.json()
    assert 'preview_html' in response_data
    
    # Verify database update
    flashcard.refresh_from_db()
    assert flashcard.front == 'Updated question'
    assert flashcard.back == 'Updated answer'
    assert flashcard.tags == ['updated', 'test']
    
    # Verify response HTML contains updated content
    preview_html = response_data['preview_html']
    assert 'Updated question' in preview_html
    assert 'Updated answer' in preview_html

def test_flashcard_update_unauthorized(client, user):
    # Create a flashcard
    flashcard = FlashcardFactory(user=user)
    
    # Try to update without authentication
    url = f'/api/flashcards/{flashcard.id}/'
    response = client.put(
        url,
        data=json.dumps({'front': 'Unauthorized update'}),
        content_type='application/json'
    )
    
    # Check unauthorized response
    assert response.status_code == 403
    
    # Verify database not updated
    flashcard.refresh_from_db()
    assert flashcard.front != 'Unauthorized update'

def test_flashcard_update_other_user(authenticated_client, user):
    # Create a flashcard owned by another user
    other_user = UserFactory()
    flashcard = FlashcardFactory(user=other_user)
    
    # Try to update other user's flashcard
    url = f'/api/flashcards/{flashcard.id}/'
    response = authenticated_client.put(
        url,
        data=json.dumps({'front': 'Other user update'}),
        content_type='application/json'
    )
    
    # Check not found response (DRF filters queryset by user)
    assert response.status_code == 404
    
    # Verify database not updated
    flashcard.refresh_from_db()
    assert flashcard.front != 'Other user update'

def test_flashcard_update_invalid_data(authenticated_client, user):
    # Create a flashcard
    flashcard = FlashcardFactory(user=user)
    original_front = flashcard.front
    
    # Try to update with empty required field
    url = f'/api/flashcards/{flashcard.id}/'
    response = authenticated_client.put(
        url,
        data=json.dumps({'front': '', 'back': 'Valid back'}),
        content_type='application/json'
    )
    
    # Check validation error response
    assert response.status_code == 400
    
    # Verify database not updated
    flashcard.refresh_from_db()
    assert flashcard.front == original_front

def test_flashcard_update_readonly_fields(authenticated_client, user):
    # Create a flashcard with some review data
    flashcard = FlashcardFactory(
        user=user,
        front_review_count=5,
        front_easiness_factor=2.1
    )
    
    # Try to update readonly fields
    url = f'/api/flashcards/{flashcard.id}/'
    response = authenticated_client.put(
        url,
        data=json.dumps({
            'front': 'Valid update',
            'back': flashcard.back,  # Include the original back field
            'front_review_count': 0,
            'front_easiness_factor': 1.0
        }),
        content_type='application/json'
    )
    
    # Check successful response (readonly fields ignored)
    assert response.status_code == 200
    
    # Verify only editable fields were updated
    flashcard.refresh_from_db()
    assert flashcard.front == 'Valid update'
    assert flashcard.front_review_count == 5  # unchanged
    assert flashcard.front_easiness_factor == 2.1  # unchanged

def test_flashcard_review_with_notes(authenticated_client, user):
    # Create a flashcard
    flashcard = FlashcardFactory(user=user)
    
    # Test front side review with notes
    url = f'/api/flashcards/{flashcard.id}/review/'
    front_review_data = {
        'status': 'hard',
        'side': 'front',
        'notes': 'Need to study this concept more'
    }
    response = authenticated_client.post(
        url,
        data=json.dumps(front_review_data),
        content_type='application/json'
    )
    
    # Check response
    assert response.status_code == 200
    response_data = response.json()
    assert 'updated_preview' in response_data
    assert 'updated_card_id' in response_data
    assert str(flashcard.id) == response_data['updated_card_id']
    
    # Verify front notes updated
    flashcard.refresh_from_db()
    assert flashcard.front_notes == 'Need to study this concept more'
    assert flashcard.back_notes is None  # Back notes should be unchanged
    
    # Test back side review with notes
    back_review_data = {
        'status': 'easy',
        'side': 'back',
        'notes': 'Good explanation, remember the example'
    }
    response = authenticated_client.post(
        url,
        data=json.dumps(back_review_data),
        content_type='application/json'
    )
    
    # Check response
    assert response.status_code == 200
    response_data = response.json()
    assert 'updated_preview' in response_data
    assert 'updated_card_id' in response_data
    assert str(flashcard.id) == response_data['updated_card_id']
    
    # Verify back notes updated while front notes remain unchanged
    flashcard.refresh_from_db()
    assert flashcard.front_notes == 'Need to study this concept more'  # Front notes should be unchanged
    assert flashcard.back_notes == 'Good explanation, remember the example'
