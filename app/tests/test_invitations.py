import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from main.models import Invitation
from django.test import Client
from tests.factories import UserFactory, InvitationFactory

pytestmark = pytest.mark.django_db

@pytest.fixture
def admin_client():
    """Create a client with an admin user"""
    admin = UserFactory(is_staff=True)
    client = Client()
    client.force_login(admin)
    return client, admin

@pytest.fixture
def regular_client():
    """Create a client with a regular user"""
    user = UserFactory(is_staff=False)
    client = Client()
    client.force_login(user)
    return client, user

@pytest.fixture
def invitation():
    """Create a test invitation"""
    return InvitationFactory()

@pytest.fixture
def accepted_invitation():
    """Create a test invitation that has been accepted"""
    user = UserFactory()
    invitation = InvitationFactory()
    invitation.accept(user)
    return invitation

# Model Tests
def test_invitation_model_creation():
    """Test that an invitation can be created"""
    admin = UserFactory(is_staff=True)
    invitation = Invitation.objects.create(
        email="test@example.com",
        invited_by=admin
    )
    assert invitation.id is not None
    assert invitation.email == "test@example.com"
    assert invitation.invited_by == admin
    assert invitation.is_accepted is False

def test_invitation_accept_method():
    """Test the accept method on the Invitation model"""
    invitation = InvitationFactory()
    user = UserFactory()
    
    assert invitation.is_accepted is False
    invitation.accept(user)
    assert invitation.is_accepted is True
    assert invitation.accepted_by == user

# View Tests
def test_invite_user_view_admin_access(admin_client):
    """Test that admins can access the invite user view"""
    client, _ = admin_client
    response = client.get(reverse('main:invite_user'))
    assert response.status_code == 200
    assert 'form' in response.context

def test_invite_user_view_regular_user_access(regular_client):
    """Test that regular users cannot access the invite user view"""
    client, _ = regular_client
    response = client.get(reverse('main:invite_user'))
    assert response.status_code == 302  # Should redirect

def test_list_invitations_view_admin_access(admin_client):
    """Test that admins can access the list invitations view"""
    client, _ = admin_client
    response = client.get(reverse('main:list_invitations'))
    assert response.status_code == 200
    assert 'invitations' in response.context

def test_list_invitations_view_regular_user_access(regular_client):
    """Test that regular users cannot access the list invitations view"""
    client, _ = regular_client
    response = client.get(reverse('main:list_invitations'))
    assert response.status_code == 302  # Should redirect

def test_create_invitation(admin_client):
    """Test that an admin can create an invitation"""
    client, admin = admin_client
    email = "newinvite@example.com"
    
    response = client.post(reverse('main:invite_user'), {'email': email})
    assert response.status_code == 200
    
    # Check that the invitation was created
    invitation = Invitation.objects.filter(email=email).first()
    assert invitation is not None
    assert invitation.invited_by == admin
    assert invitation.is_accepted is False

def test_delete_invitation(admin_client, invitation):
    """Test that an admin can delete an invitation"""
    client, _ = admin_client
    
    # Get the invitation ID before deletion
    invitation_id = invitation.id
    
    # Delete the invitation
    response = client.post(reverse('main:delete_invitation', args=[invitation_id]))
    assert response.status_code == 302  # Should redirect
    
    # Check that the invitation was deleted
    assert not Invitation.objects.filter(id=invitation_id).exists()

def test_delete_accepted_invitation_disables_user(admin_client):
    """Test that deleting an accepted invitation disables the associated user"""
    client, _ = admin_client
    
    # Create a user and an invitation
    user = UserFactory(is_staff=False)
    invitation = InvitationFactory()
    invitation.accept(user)
    
    # Delete the invitation
    response = client.post(reverse('main:delete_invitation', args=[invitation.id]))
    assert response.status_code == 302  # Should redirect
    
    # Check that the user was disabled
    user.refresh_from_db()
    assert user.is_active is False

# Authentication Tests
def test_signup_with_invitation():
    """Test that a user can sign up with a valid invitation"""
    invitation = InvitationFactory()
    
    # Create a client
    client = Client()
    
    # Try to sign up with the invitation
    login_url = reverse('account_login') + f"?invitation_id={invitation.id}"
    response = client.get(login_url)
    assert response.status_code == 200
    
    # Check for login page with invitation context
    assert "Accept Invitation" in str(response.content)
    
    # Submit the form to create a new account
    response = client.post(login_url, {
        'login': invitation.email,
        'password': 'testpassword123'
    })
    
    # Check that the user was created and logged in
    assert User.objects.filter(email=invitation.email).exists()
    
    # Check that the invitation was marked as accepted
    invitation.refresh_from_db()
    assert invitation.is_accepted is True

def test_signup_without_invitation():
    """Test that a user cannot sign up without an invitation"""
    client = Client()
    
    # Try to sign up without an invitation
    response = client.post(reverse('account_login'), {
        'login': 'noinvite@example.com',
        'password': 'testpassword123'
    })
    
    # Check that the user was not created
    assert not User.objects.filter(email='noinvite@example.com').exists()
