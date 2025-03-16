import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.messages import get_messages
from unittest.mock import patch
from .factories import UserFactory, DeckFactory, TutorFactory
from .test_base import BaseTestCase
from main.models import Deck, User, FlashCard, Tutor, Document
import json

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def clean_database():
    """Clean up the database before each test."""
    Deck.objects.all().delete()
    User.objects.all().delete()

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def tutor():
    return TutorFactory()

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client
def test_tutor_list_view(authenticated_client, user, tutor):
    # Test home page with single tutor
    response = authenticated_client.get(reverse('main:home'))
    assert response.status_code == 302
    assert response.url == reverse('main:deck_list', kwargs={'url_path': tutor.url_path})

    # Create another tutor
    other_tutor = TutorFactory()

    # Test home page with multiple tutors
    response = authenticated_client.get(reverse('main:home'))
    assert response.status_code == 200
    assert tutor.name in str(response.content)
    assert other_tutor.name in str(response.content)

def test_deck_list_view(authenticated_client, user, tutor):
    # Test empty deck list redirects to create
    response = authenticated_client.get(reverse('main:deck_list', kwargs={'url_path': tutor.url_path}))

    assert response.status_code == 302
    assert response.url == reverse('main:deck_create', kwargs={'url_path': tutor.url_path})
    # Create a deck
    deck = DeckFactory(owner=user, tutor=tutor)

    # Test deck list with deck
    response = authenticated_client.get(reverse('main:deck_list', kwargs={'url_path': tutor.url_path}))
    assert response.status_code == 200
    assert deck.name in str(response.content)

    # Test that users can only see their own decks
    other_user = UserFactory()
    other_deck = DeckFactory(owner=other_user, tutor=tutor)
    assert other_deck.name not in str(response.content)

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

def tutor_config():
    return {
        'prompts': {
            'generate_flashcards': {
                'system': 'You are an AI assistant tasked with generating flashcards for learning purposes.',
                'user': 'Create flashcards based on the following content:\n${content}\n\nExisting flashcards:\n${existing_flashcards}'
            }
        }
    }

@pytest.mark.focus
def test_deck_create_view_with_questions(authenticated_client, user, tutor, mock_openai_response):
    data = {
        'name': 'Software Engineer at Google',
        'status': 'draft',
        'content': json.dumps(mock_openai_response),
        'document': ['This is the content of the document.']
    }

    # Mock the OpenAI call
    with patch.object(Tutor, 'get_config', return_value=tutor_config()):
        with patch('main.models.call_openai', return_value=json.dumps(mock_openai_response)):
            before_count = Deck.objects.count()
            response = authenticated_client.post(reverse('main:deck_create', kwargs={'url_path': tutor.url_path}), data)

            # Check deck was created
            assert Deck.objects.count() == before_count + 1
            deck = Deck.objects.first()
            assert deck.owner == user
            assert deck.tutor == tutor
            assert deck.name == data['name']

            # Check flashcards were created
            flashcards = deck.flashcards.all()
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

            # Check document was created
            # document = Document.objects.first()
            # assert document.name == f"{deck.name} Document"
            # assert document.owner == user
            # assert document.deck == deck
            # assert document.content == data['document_content']

            assert response.status_code == 302
            assert response.url == reverse('main:deck_detail', kwargs={'url_path': tutor.url_path, 'pk': deck.pk})

def test_deck_create_view_openai_error(authenticated_client, user, tutor):
    data = {
        'name': 'Software Engineer at Google',
        'status': 'draft',
        'deck_type': Deck.DeckType.JOB_APPLICATION
    }

    # Mock OpenAI call to raise an exception
    with patch.object(Tutor, 'get_config', return_value=tutor_config()):
        with patch('main.models.call_openai', side_effect=Exception("OpenAI API error")):
            before_count = Deck.objects.count()
            response = authenticated_client.post(reverse('main:deck_create', kwargs={'url_path': tutor.url_path}), data)
            # Check deck was still created despite the error
            assert Deck.objects.count() == before_count + 1
            deck = Deck.objects.first()
            assert deck.owner == user
            assert deck.tutor == tutor
            assert deck.name == data['name']

            # Check no flashcards were created
            assert deck.flashcards.count() == 0

            assert response.status_code == 302
            assert response.url == reverse('main:deck_detail', kwargs={'url_path': tutor.url_path, 'pk': deck.pk})

def test_deck_edit_view_with_questions(authenticated_client, user, tutor, mock_openai_response):
    # Create deck with existing flashcards
    deck = DeckFactory(owner=user, tutor=tutor)
    existing_flashcard = FlashCard.objects.create(
        user=user,
        front="Existing question",
        back="Existing answer",
        tags=["HR", "auto-generated"]
    )
    existing_flashcard.decks.add(deck)

    data = {
        'name': 'Updated Job Title',
        'status': 'submitted',
        'content': "MY RESUME",
    }

    # Mock OpenAI call
    with patch.object(Tutor, 'get_config', return_value=tutor_config()):
        with patch('main.models.call_openai', return_value=json.dumps(mock_openai_response)):
            response = authenticated_client.post(
                reverse('main:deck_edit', kwargs={'url_path': tutor.url_path, 'pk': deck.pk}),
                data
            )

            deck.refresh_from_db()
            assert deck.name == data['name']

            # Check new flashcards were added
            flashcards = deck.flashcards.all()
            assert flashcards.count() == 3  # 1 existing + 2 new

            # Verify the existing flashcard is still there
            assert flashcards.filter(front="Existing question").exists()

            # Verify new flashcards were added
            new_questions = [card.front for card in flashcards if card.front != "Existing question"]
            assert mock_openai_response[0]['question'] in new_questions
            assert mock_openai_response[1]['question'] in new_questions

class TestDeckViews(BaseTestCase):
    def test_deck_edit_view_openai_error(self):
        user = self.create_and_login_user()
        tutor = TutorFactory()
        deck = DeckFactory(owner=user, tutor=tutor)
        existing_flashcard = FlashCard.objects.create(
            user=user,
            front="Existing question",
            back="Existing answer",
            tags=["HR", "auto-generated"]
        )
        existing_flashcard.decks.add(deck)

        data = {
            'name': 'Updated Job Title',
            'status': 'submitted',
            'content': "MY RESUME",
        }

        original_name = deck.name
        error_message = "OpenAI API error"

        # Mock OpenAI call to raise an exception
        with patch.object(Tutor, 'get_config', return_value=tutor_config()):
            with patch('main.models.call_openai', side_effect=Exception(error_message)):
                    response = self.client.post(
                        reverse('main:deck_edit', kwargs={'url_path': tutor.url_path, 'pk': deck.pk}),
                        data
                    )

                    # Check that we're re-rendering the form
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('main/deck_form.html', [t.name for t in response.templates])

                    # Check that error message is in the response
                    messages = self.get_messages_list(response)

                    self.assertEqual(len(messages), 1)
                    message = messages[0]
                    self.assertEqual(message.tags, 'error')
                    self.assertIn('Failed to generate interview questions', str(message))

                    # Check that form contains the submitted data
                    self.assertIn(data['name'], str(response.content))

                    # Check that we have the retry flag
                    self.assertTrue(response.context['is_retry'])

                    # Check that error message is in the context
                    self.assertEqual(
                        response.context['error_message'],
                        f"Error generating questions: {error_message}"
                    )

                    # Check that deck was not updated
                    deck.refresh_from_db()
                    self.assertEqual(deck.name, original_name)

                    # Check existing flashcard remains unchanged
                    flashcards = deck.flashcards.all()
                    self.assertEqual(flashcards.count(), 1)
                    self.assertEqual(flashcards.first().front, "Existing question")

def test_deck_delete_view(authenticated_client, user, tutor):
    deck = DeckFactory(owner=user, tutor=tutor)

    before_count = Deck.objects.count()
    response = authenticated_client.post(reverse('main:deck_delete', kwargs={'url_path': tutor.url_path, 'pk': deck.pk}))
    assert Deck.objects.count() == before_count - 1
    assert response.status_code == 302
    assert response.url == reverse('main:deck_list', kwargs={'url_path': tutor.url_path})

def test_deck_detail_view(authenticated_client, user, tutor):
    deck = DeckFactory(owner=user, tutor=tutor)

    response = authenticated_client.get(reverse('main:deck_detail', kwargs={'url_path': tutor.url_path, 'pk': deck.pk}))
    assert response.status_code == 200
    assert response.context['tutor'] == tutor
    assert response.context['deck'] == deck

def test_unauthorized_access(client, tutor):
    user = UserFactory()
    deck = DeckFactory(owner=user, tutor=tutor)

    # Test list view requires login
    response = client.get(reverse('main:deck_list', kwargs={'url_path': tutor.url_path}))
    assert response.status_code == 302  # Redirects to login

    # Test detail view requires login
    response = client.get(reverse('main:deck_detail', kwargs={'url_path': tutor.url_path, 'pk': deck.pk}))
    assert response.status_code == 302  # Redirects to login

    # Test create view requires login
    response = client.get(reverse('main:deck_create', kwargs={'url_path': tutor.url_path}))
    assert response.status_code == 302  # Redirects to login

    # Test edit view requires login
    response = client.get(reverse('main:deck_edit', kwargs={'url_path': tutor.url_path, 'pk': deck.pk}))
    assert response.status_code == 302  # Redirects to login

    # Test delete view requires login
    response = client.get(reverse('main:deck_delete', kwargs={'url_path': tutor.url_path, 'pk': deck.pk}))
    assert response.status_code == 302  # Redirects to login

def test_other_user_access(authenticated_client, user, tutor):
    other_user = UserFactory()
    other_deck = DeckFactory(owner=other_user, tutor=tutor)

    # Test cannot access other user's deck detail
    response = authenticated_client.get(reverse('main:deck_detail', kwargs={'url_path': tutor.url_path, 'pk': other_deck.pk}))
    assert response.status_code == 404

    # Test cannot edit other user's deck
    response = authenticated_client.post(
        reverse('main:deck_edit', kwargs={'url_path': tutor.url_path, 'pk': other_deck.pk}),
        {'name': 'Hacked', 'status': 'draft', 'resume': 'hacked', 'job_description': 'hacked'}
    )
    assert response.status_code == 404
    other_deck.refresh_from_db()
    assert other_deck.name != 'Hacked'

    # Test cannot delete other user's deck
    response = authenticated_client.post(reverse('main:deck_delete', kwargs={'url_path': tutor.url_path, 'pk': other_deck.pk}))
    assert response.status_code == 404
    assert Deck.objects.filter(pk=other_deck.pk).exists()

    # Test cannot generate questions for other user's deck
    response = authenticated_client.post(reverse('main:api-deck-generate-questions', kwargs={'url_path': tutor.url_path, 'pk': other_deck.pk}))
    assert response.status_code == 404

@pytest.mark.django_db
def test_generate_questions_model_method(user, tutor, mock_openai_response):
    """Test the generate_and_save_flashcards method on Deck model"""
    deck = DeckFactory(owner=user, tutor=tutor, content="MY RESUME")

    with patch.object(Tutor, 'get_config', return_value=tutor_config()):
        with patch('main.models.call_openai', return_value=json.dumps(mock_openai_response)):
            # Test generating questions
            created_cards = deck.generate_and_save_flashcards()

            # Verify cards were created
            assert len(created_cards) == 2

            # Verify card content
            for card in created_cards:
                assert card.user == user
                assert 'auto-generated' in card.tags
                assert card.decks.filter(pk=deck.pk).exists()

                # Verify question content matches mock data
                matching_q = next(q for q in mock_openai_response if q['question'] == card.front)
                assert card.back == matching_q['suggested_answer']
                assert matching_q['category'] in card.tags

@pytest.mark.django_db
def test_generate_questions_endpoint(authenticated_client, user, tutor, mock_openai_response):
    """Test the generate questions endpoint"""
    deck = DeckFactory(owner=user, tutor=tutor, content="MY RESUME")

    with patch.object(Tutor, 'get_config', return_value=tutor_config()):
        with patch('main.models.call_openai', return_value=json.dumps(mock_openai_response)):
            # Make request to generate questions
            response = authenticated_client.post(
                reverse('main:api-deck-generate-questions', kwargs={'url_path': tutor.url_path, 'pk': deck.pk})
            )

        # Verify successful response
        assert response.status_code == 200
        assert response.json()['message'] == 'Generated 2 new questions!'

        # Verify cards were created
        flashcards = deck.flashcards.all()
        assert flashcards.count() == 2

        # Check flashcard content
        flashcard_questions = set(card.front for card in flashcards)
        expected_questions = set(q['question'] for q in mock_openai_response)
        assert flashcard_questions == expected_questions

@pytest.mark.django_db
def test_generate_questions_error_handling(authenticated_client, user, tutor):
    """Test error handling in generate questions endpoint"""
    deck = DeckFactory(owner=user, tutor=tutor, content="MY RESUME")

    with patch.object(Tutor, 'get_config', return_value=tutor_config()):
        with patch('main.models.call_openai', side_effect=Exception('API Error')):
            # Make request to generate questions
            response = authenticated_client.post(
                reverse('main:api-deck-generate-questions', kwargs={'url_path': tutor.url_path, 'pk': deck.pk})
            )

            # Verify error response
            assert response.status_code == 500
            assert response.json()['message'] == 'Failed to generate questions'

            # Verify no cards were created
            assert deck.flashcards.count() == 0
