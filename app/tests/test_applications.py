import pytest
from django.urls import reverse
from django.test import Client
from unittest.mock import patch
from .factories import UserFactory, ApplicationFactory
from main.models import Application, User, FlashCard
import json

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def clean_database():
    """Clean up the database before each test."""
    Application.objects.all().delete()
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
def test_application_list_view(authenticated_client, user):
    application = ApplicationFactory(owner=user)
    
    response = authenticated_client.get(reverse('main:application_list'))
    assert response.status_code == 200
    assert application.name in str(response.content)
    
    # Test that users can only see their own applications
    other_user = UserFactory()
    other_application = ApplicationFactory(owner=other_user)
    assert other_application.name not in str(response.content)

@pytest.fixture
def mock_openai_response():
    return [
        {
            "question": "Tell me about a challenging project you worked on?",
            "category": "Technical",
            "suggested_answer": "Use STAR format to describe a specific project..."
        },
        {
            "question": "How do you handle conflicts in a team?",
            "category": "Cultural Fit",
            "suggested_answer": "Describe a specific situation where..."
        }
    ]

def test_application_create_view_with_questions(authenticated_client, user, mock_openai_response):
    data = {
        'name': 'Software Engineer at Google',
        'status': 'draft',
        'resume': 'My resume content',
        'job_description': 'Job description content'
    }
    
    # Mock the OpenAI call
    with patch('main.ai_helpers.call_openai', return_value=json.dumps(mock_openai_response)):
        before_count = Application.objects.count()
        response = authenticated_client.post(reverse('main:application_create'), data)
        
        # Check application was created
        assert Application.objects.count() == before_count + 1
        application = Application.objects.first()
        assert application.owner == user
        assert application.name == data['name']
        
        # Check flashcards were created
        flashcards = application.flashcards.all()
        assert flashcards.count() == 2
        
        # Check flashcard content (order may vary)
        flashcard_questions = set(card.front for card in flashcards)
        expected_questions = set(q['question'] for q in mock_openai_response)
        assert flashcard_questions == expected_questions
        
        # Check tags and answers are correctly matched
        for card in flashcards:
            matching_q = next(q for q in mock_openai_response if q['question'] == card.front)
            assert card.back == matching_q['suggested_answer']
            assert matching_q['category'] in card.tags
            assert 'auto-generated' in card.tags
        
        assert response.status_code == 302
        assert response.url == reverse('main:application_detail', kwargs={'pk': application.pk})

def test_application_create_view_openai_error(authenticated_client, user):
    data = {
        'name': 'Software Engineer at Google',
        'status': 'draft',
        'resume': 'My resume content',
        'job_description': 'Job description content'
    }
    
    # Mock OpenAI call to raise an exception
    with patch('main.models.generate_interview_questions') as mock_generate:
        mock_generate.side_effect = Exception("OpenAI API error")
        
        before_count = Application.objects.count()
        response = authenticated_client.post(reverse('main:application_create'), data)
        
        # Check application was still created despite the error
        assert Application.objects.count() == before_count + 1
        application = Application.objects.first()
        assert application.owner == user
        assert application.name == data['name']
        
        # Check no flashcards were created
        assert application.flashcards.count() == 0
        
        assert response.status_code == 302
        assert response.url == reverse('main:application_detail', kwargs={'pk': application.pk})

def test_application_edit_view_with_questions(authenticated_client, user, mock_openai_response):
    # Create application with existing flashcards
    application = ApplicationFactory(owner=user)
    existing_flashcard = FlashCard.objects.create(
        user=user,
        front="Existing question",
        back="Existing answer",
        tags=["HR", "auto-generated"]
    )
    existing_flashcard.applications.add(application)
    
    data = {
        'name': 'Updated Job Title',
        'status': 'submitted',
        'resume': 'Updated resume',
        'job_description': 'Updated job description'
    }
    
    # Mock OpenAI call
    with patch('main.ai_helpers.call_openai', return_value=json.dumps(mock_openai_response)):
        response = authenticated_client.post(
            reverse('main:application_edit', kwargs={'pk': application.pk}),
            data
        )
        
        application.refresh_from_db()
        assert application.name == data['name']
        
        # Check new flashcards were added
        flashcards = application.flashcards.all()
        assert flashcards.count() == 3  # 1 existing + 2 new
        
        # Verify the existing flashcard is still there
        assert flashcards.filter(front="Existing question").exists()
        
        # Verify new flashcards were added
        new_questions = [card.front for card in flashcards if card.front != "Existing question"]
        assert mock_openai_response[0]['question'] in new_questions
        assert mock_openai_response[1]['question'] in new_questions

def test_application_edit_view_openai_error(authenticated_client, user):
    application = ApplicationFactory(owner=user)
    existing_flashcard = FlashCard.objects.create(
        user=user,
        front="Existing question",
        back="Existing answer",
        tags=["HR", "auto-generated"]
    )
    existing_flashcard.applications.add(application)
    
    data = {
        'name': 'Updated Job Title',
        'status': 'submitted',
        'resume': 'Updated resume',
        'job_description': 'Updated job description'
    }
    
    # Mock OpenAI call to raise an exception
    with patch('main.ai_helpers.call_openai', side_effect=Exception("OpenAI API error")):
        response = authenticated_client.post(
            reverse('main:application_edit', kwargs={'pk': application.pk}),
            data
        )
        
        application.refresh_from_db()
        assert application.name == data['name']
        
        # Check existing flashcard remains unchanged
        flashcards = application.flashcards.all()
        assert flashcards.count() == 1
        assert flashcards.first().front == "Existing question"

def test_application_delete_view(authenticated_client, user):
    application = ApplicationFactory(owner=user)
    
    before_count = Application.objects.count()
    response = authenticated_client.post(reverse('main:application_delete', kwargs={'pk': application.pk}))
    assert Application.objects.count() == before_count - 1
    assert response.status_code == 302
    assert response.url == reverse('main:application_list')

def test_application_detail_view(authenticated_client, user):
    application = ApplicationFactory(owner=user)
    
    response = authenticated_client.get(reverse('main:application_detail', kwargs={'pk': application.pk}))
    assert response.status_code == 200
    assert application.title in str(response.content)
    
def test_unauthorized_access(client):
    user = UserFactory()
    application = ApplicationFactory(owner=user)
    
    # Test list view requires login
    response = client.get(reverse('main:application_list'))
    assert response.status_code == 302  # Redirects to login
    
    # Test detail view requires login
    response = client.get(reverse('main:application_detail', kwargs={'pk': application.pk}))
    assert response.status_code == 302  # Redirects to login
    
    # Test create view requires login
    response = client.get(reverse('main:application_create'))
    assert response.status_code == 302  # Redirects to login
    
    # Test edit view requires login
    response = client.get(reverse('main:application_edit', kwargs={'pk': application.pk}))
    assert response.status_code == 302  # Redirects to login
    
    # Test delete view requires login
    response = client.get(reverse('main:application_delete', kwargs={'pk': application.pk}))
    assert response.status_code == 302  # Redirects to login

def test_other_user_access(authenticated_client, user):
    other_user = UserFactory()
    other_application = ApplicationFactory(owner=other_user)
    
    # Test cannot access other user's application detail
    response = authenticated_client.get(reverse('main:application_detail', kwargs={'pk': other_application.pk}))
    assert response.status_code == 404
    
    # Test cannot edit other user's application
    response = authenticated_client.post(
        reverse('main:application_edit', kwargs={'pk': other_application.pk}),
        {'name': 'Hacked', 'status': 'draft', 'resume': 'hacked', 'job_description': 'hacked'}
    )
    assert response.status_code == 404
    other_application.refresh_from_db()
    assert other_application.name != 'Hacked'
    
    # Test cannot delete other user's application
    response = authenticated_client.post(reverse('main:application_delete', kwargs={'pk': other_application.pk}))
    assert response.status_code == 404
    assert Application.objects.filter(pk=other_application.pk).exists()
    
    # Test cannot generate questions for other user's application
    response = authenticated_client.post(reverse('main:generate_questions', kwargs={'pk': other_application.pk}))
    assert response.status_code == 404

@pytest.mark.django_db
def test_generate_questions_model_method(user, mock_openai_response):
    """Test the generate_and_save_questions method on Application model"""
    application = ApplicationFactory(owner=user)
    
    with patch('main.ai_helpers.call_openai', return_value=json.dumps(mock_openai_response)):
        # Test generating questions
        created_cards = application.generate_and_save_questions()
        
        # Verify cards were created
        assert len(created_cards) == 2
        
        # Verify card content
        for card in created_cards:
            assert card.user == user
            assert 'auto-generated' in card.tags
            assert card.applications.filter(pk=application.pk).exists()
            
            # Verify question content matches mock data
            matching_q = next(q for q in mock_openai_response if q['question'] == card.front)
            assert card.back == matching_q['suggested_answer']
            assert matching_q['category'] in card.tags

@pytest.mark.django_db
def test_generate_questions_endpoint(authenticated_client, user, mock_openai_response):
    """Test the generate questions endpoint"""
    application = ApplicationFactory(owner=user)
    
    with patch('main.ai_helpers.call_openai', return_value=json.dumps(mock_openai_response)):
        # Make request to generate questions
        response = authenticated_client.post(
            reverse('main:generate_questions', kwargs={'pk': application.pk})
        )
        
        # Verify redirect response
        assert response.status_code == 302
        assert response.url == reverse('main:application_detail', kwargs={'pk': application.pk})
        
        # Verify success message
        messages = list(response.wsgi_request._messages)
        assert len(messages) == 1
        assert 'Generated 2 new questions!' in str(messages[0])
        
        # Verify cards were created
        flashcards = application.flashcards.all()
        assert flashcards.count() == 2
        
        # Check flashcard content
        flashcard_questions = set(card.front for card in flashcards)
        expected_questions = set(q['question'] for q in mock_openai_response)
        assert flashcard_questions == expected_questions

@pytest.mark.django_db
def test_generate_questions_error_handling(authenticated_client, user):
    """Test error handling in generate questions endpoint"""
    application = ApplicationFactory(owner=user)
    
    with patch('main.ai_helpers.call_openai', side_effect=Exception('API Error')):
        # Make request to generate questions
        response = authenticated_client.post(
            reverse('main:generate_questions', kwargs={'pk': application.pk})
        )
        
        # Verify redirect response
        assert response.status_code == 302
        assert response.url == reverse('main:application_detail', kwargs={'pk': application.pk})
        
        # Verify error message
        messages = list(response.wsgi_request._messages)
        assert len(messages) == 1
        assert 'Failed to generate new questions' in str(messages[0])
        
        # Verify no cards were created
        assert application.flashcards.count() == 0
