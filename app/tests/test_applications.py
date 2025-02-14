import pytest
from django.urls import reverse
from django.test import Client
from .factories import UserFactory, ApplicationFactory
from main.models import Application, User

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

def test_application_create_view(authenticated_client, user):
    data = {
        'name': 'Software Engineer at Google',
        'status': 'draft',
        'resume': 'My resume content',
        'job_description': 'Job description content'
    }
    
    before_count = Application.objects.count()
    response = authenticated_client.post(reverse('main:application_create'), data)
    assert Application.objects.count() == before_count + 1
    application = Application.objects.first()
    assert application.owner == user
    assert application.name == data['name']
    assert response.status_code == 302
    assert response.url == reverse('main:application_detail', kwargs={'pk': application.pk})

def test_application_edit_view(authenticated_client, user):
    application = ApplicationFactory(owner=user)
    data = {
        'name': 'Updated Job Title',
        'status': 'submitted',
        'resume': application.resume,
        'job_description': application.job_description
    }
    
    response = authenticated_client.post(
        reverse('main:application_edit', kwargs={'pk': application.pk}),
        data
    )
    application.refresh_from_db()
    assert application.name == data['name']
    assert application.status == data['status']
    assert response.status_code == 302
    assert response.url == reverse('main:application_detail', kwargs={'pk': application.pk})

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
    assert application.name in str(response.content)
    assert application.get_status_display() in str(response.content)

def test_unauthorized_access(client):
    user = UserFactory()
    application = ApplicationFactory(owner=user)
    
    # Test list view requires login
    response = client.get(reverse('main:application_list'))
    assert response.status_code == 302  # Redirects to login
    
    # Test detail view requires login
    response = client.get(reverse('main:application_detail', kwargs={'pk': application.pk}))
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
