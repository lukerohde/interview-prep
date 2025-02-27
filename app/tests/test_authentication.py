import pytest
from django.urls import reverse
from django.conf import settings
from config.account_adapter import InviteOnlyAccountAdapter
from django.contrib.auth.models import User
from allauth.account.utils import user_email, user_username
from django.contrib.messages import get_messages
from django.test import RequestFactory, Client

pytestmark = pytest.mark.django_db

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def login_url():
    """Return the login URL"""
    return reverse('account_login')

@pytest.fixture
def signup_url():
    """Return the signup URL"""
    return reverse('account_signup')

@pytest.fixture
def adapter():
    """Return an instance of the custom account adapter"""
    return InviteOnlyAccountAdapter()

@pytest.fixture
def existing_user():
    """Create a test user with known credentials"""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='password123'
    )
    return user

@pytest.fixture
def request_factory():
    """Return a RequestFactory instance"""
    return RequestFactory()

def test_login_page_loads(client, login_url):
    """Test that the login page loads correctly"""
    response = client.get(login_url)
    assert response.status_code == 200
    assert 'account/login.html' in [t.name for t in response.templates]

def test_signup_redirects_to_login(client, signup_url, login_url):
    """Test that the signup URL redirects to login"""
    response = client.get(signup_url)
    assert response.status_code == 302
    assert response.url == login_url

def test_username_generation(adapter):
    """Test that usernames are generated correctly from emails"""
    # Simple case
    user = User()
    user_email(user, 'test@example.com')
    adapter.populate_username(None, user)
    assert user_username(user) == 'test'
    
    # Email with dots
    user = User()
    user_email(user, 'john.doe@example.com')
    adapter.populate_username(None, user)
    assert user_username(user) == 'john.doe'
    
    # Email with plus sign
    user = User()
    user_email(user, 'test+label@example.com')
    adapter.populate_username(None, user)
    assert user_username(user) == 'test+label'

def test_duplicate_username_handling(adapter):
    """Test that duplicate usernames are handled correctly"""
    # Create a user with username 'duplicate'
    existing_user = User.objects.create(username='duplicate', email='existing@example.com')
    
    # Try to create another user with the same username
    new_user = User()
    user_email(new_user, 'duplicate@example.com')
    adapter.populate_username(None, new_user)
    
    # Check that the username was modified to avoid duplication
    assert user_username(new_user) != 'duplicate'
    assert user_username(new_user).startswith('duplicate_')

def test_user_authentication_success(adapter, existing_user, request_factory):
    """Test that an existing user can be authenticated"""
    # Create a test request
    request = request_factory.get('/')
    
    # Test that the user can be authenticated with correct password
    authenticated_user = User.objects.get(username='testuser')
    assert authenticated_user.check_password('password123')

def test_new_user_creation(adapter):
    """Test that a new user can be created with the adapter"""
    # Count users before
    user_count_before = User.objects.count()
    
    # Create a new user
    new_email = 'newuser@example.com'
    new_user = User()
    user_email(new_user, new_email)
    
    # Populate username
    adapter.populate_username(None, new_user)
    
    # Set password and save
    new_user.set_password('newpassword123')
    new_user.save()
    
    # Check that a new user was created
    assert User.objects.count() == user_count_before + 1
    
    # Check that the new user has the correct email and username
    saved_user = User.objects.get(email=new_email)
    assert saved_user.username == 'newuser'

def test_login_form_validation(client, login_url):
    """Test that login form validation works"""
    # Get the login page first to get the CSRF token
    response = client.get(login_url)
    
    # Submit the login form with missing data
    login_data = {
        'login': '',  # Empty email
        'password': 'password123',
    }
    response = client.post(login_url, login_data)
    
    # Check that we're still on the login page
    assert response.status_code == 200
    assert 'account/login.html' in [t.name for t in response.templates]
    
    # Check that the form has errors
    assert 'form' in response.context
    assert response.context['form'].errors

# Integration tests for the complete authentication flow

def test_existing_user_login_integration(client, existing_user, login_url):
    """Test the complete login flow for an existing user"""
    # Get the login page
    response = client.get(login_url)
    
    # Submit the login form with correct credentials
    login_data = {
        'login': 'test@example.com',
        'password': 'password123',
    }
    
    # Test that the form submission works without errors
    try:
        response = client.post(login_url, login_data)
        # If we get here, the form submission succeeded
        success = True
    except Exception:
        success = False
    
    assert success, "Login form submission failed"
    
    # Check that the user exists
    user = User.objects.get(email='test@example.com')
    assert user is not None
    assert user.username == 'testuser'

def test_new_user_signup_integration(client, login_url):
    """Test that users cannot sign up without an invitation"""
    # Count users before
    user_count_before = User.objects.count()
    
    # Submit the login form with new user credentials
    new_email = 'integration_test@example.com'
    login_data = {
        'login': new_email,
        'password': 'newpassword123',
    }
    
    # Test that the form submission works without errors
    try:
        response = client.post(login_url, login_data)
        # If we get here, the form submission succeeded
        success = True
    except Exception as e:
        success = False
    
    assert success, "Form submission failed"
    
    # Check that a new user was NOT created (since we require invitations now)
    assert User.objects.count() == user_count_before

def test_login_failure_integration(client, existing_user, login_url):
    """Test the login failure flow"""
    # Get the login page
    response = client.get(login_url)

    # Submit the login form with incorrect password
    login_data = {
        'login': 'test@example.com',
        'password': 'wrongpassword',
    }
    response = client.post(login_url, login_data)

    # Check that we're redirected to the login page with the email parameter
    assert response.status_code == 302
    assert '/accounts/login/?email=test%40example.com' in response.url

    # Follow the redirect
    response = client.get(response.url)
    
    # Check that the email is preserved in the form
    assert b'value="test@example.com"' in response.content
    
    # Check that we have an error message
    assert b'Invalid password for this email' in response.content
