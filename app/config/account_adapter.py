from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.forms import LoginForm
from allauth.account.utils import user_email, user_username, perform_login
from allauth.account import app_settings
from allauth.exceptions import ImmediateHttpResponse
import uuid
from django import forms
from main.models import Invitation

class MergedLoginForm(LoginForm):
    """Custom login form that doesn't validate email existence"""
    
    def clean(self):
        """Override to prevent validation of email existence"""
        cleaned_data = super(forms.Form, self).clean()  # Skip LoginForm.clean()
        
        # Just validate that both fields are provided
        if not cleaned_data.get('login') or not cleaned_data.get('password'):
            self.add_error(None, "Please enter both email and password.")
            
        return cleaned_data

class MergedLoginSignupView:
    """
    A view that handles both login and signup in one form.
    If the user exists, they will be logged in.
    If the user doesn't exist, a new account will be created.
    """
    
    def __init__(self, request):
        self.request = request
        self.user = None
        self.form = MergedLoginForm(request.POST or None)
        
    def process(self):
        # If this is a signup page request, redirect to login page
        if self.request.path == '/accounts/signup/' and self.request.method == 'GET':
            return redirect('account_login')
            
        # Check if there's an invitation ID in the URL
        invitation_id = self.request.GET.get('invitation_id')
        if invitation_id and self.request.method == 'GET':
            try:
                # Look up the invitation
                invitation = Invitation.objects.get(id=invitation_id, accepted_at=None)
                # Pre-populate the email field
                self.form.initial['login'] = invitation.email
            except Invitation.DoesNotExist:
                messages.error(self.request, "Invalid or already used invitation.")
            
        if self.request.method == 'POST' and self.form.is_valid():
            email = self.form.cleaned_data.get('login')
            password = self.form.cleaned_data.get('password')
            
            # Check if user exists by email
            user = User.objects.filter(email=email).first()
            
            if user:
                # User exists, try to log them in
                return self._handle_login(user, password)
            else:
                # User doesn't exist, create a new account
                return self._handle_signup(email, password)
        
        # If not POST or form is invalid, render the form
        return render(self.request, 'account/login.html', {'form': self.form})
    
    def _handle_login(self, user, password):
        """Handle login for existing user"""
        if user.check_password(password):
            try:
                # Use allauth's perform_login to handle login
                return perform_login(
                    self.request, user,
                    redirect_url=settings.LOGIN_REDIRECT_URL
                )
            except ImmediateHttpResponse as e:
                return e.response
        else:
            # Invalid password
            self.form.add_error(None, "Invalid password for this email.")
            messages.error(self.request, "Invalid password for this email.")
            
            # Redirect back to login page with email as query parameter
            from django.urls import reverse
            from urllib.parse import urlencode
            
            email = user_email(user)
            base_url = reverse('account_login')
            query_params = urlencode({'email': email})
            redirect_url = f"{base_url}?{query_params}"
            
            return redirect(redirect_url)
    
    def _handle_signup(self, email, password):
        """Create a new user account"""
        try:
            # Check if there's an invitation for this email
            invitation = None
            
            # First check if there's an invitation ID in the URL
            invitation_id = self.request.GET.get('invitation_id')
            if invitation_id:
                try:
                    invitation = Invitation.objects.get(id=invitation_id, email__iexact=email, accepted_at=None)
                except Invitation.DoesNotExist:
                    pass
            
            # If no invitation found by ID, look up by email
            if not invitation:
                invitation = Invitation.objects.filter(email__iexact=email, accepted_at=None).first()
            
            if not invitation:
                # No invitation found, show error message
                self.form.add_error(None, "You need an invitation to sign up. Please contact an administrator.")
                messages.error(self.request, "You need an invitation to sign up. Please contact an administrator.")
                return render(self.request, 'account/login.html', {'form': self.form})
            
            # Create a new user
            user = User()
            user_email(user, email)
            
            # Generate a username from email
            adapter = InviteOnlyAccountAdapter()
            adapter.populate_username(self.request, user)
            
            # Set password and save
            user.set_password(password)
            user.save()
            
            # Mark invitation as accepted
            invitation.accept(user)
            
            # Log the user in
            try:
                return perform_login(
                    self.request, user,
                    redirect_url=settings.LOGIN_REDIRECT_URL
                )
            except ImmediateHttpResponse as e:
                return e.response
        except Exception as e:
            # Handle any errors during signup
            self.form.add_error(None, f"Error creating account: {str(e)}")
            messages.error(self.request, f"Error creating account: {str(e)}")
            return render(self.request, 'account/login.html', {'form': self.form})


class InviteOnlyAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        # Only allow signup if the email has an invitation
        if request and request.method == 'POST':
            email = request.POST.get('email')
            if email:
                # Check if there's an invitation for this email
                return Invitation.objects.filter(email__iexact=email, accepted_at=None).exists()
        return False  # Closed for signup by default
        
    def get_signup_redirect_url(self, request):
        return super().get_signup_redirect_url(request)
    
    def pre_login(self, request, user, **kwargs):
        """
        Called after a user successfully authenticates, but before they are logged in.
        Here we handle the case where a user tries to log in but doesn't have an account yet.
        
        Override to handle extra keyword arguments.
        """
        return super().pre_login(request, user, **kwargs)
    
    def get_client_ip(self, request):
        """
        Override to handle None request parameter.
        """
        if request is None:
            return "127.0.0.1"  # Return localhost IP if request is None
            
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
    
    def populate_username(self, request, user):
        """
        Fills in a valid username from email if missing.
        Django's User model requires a unique username.
        """
        email = user_email(user)
        if not user_username(user):
            # Set username to part before @ in email
            base_username = email.split('@')[0] if email else ''
            username = base_username
            
            # If username already exists, add a random suffix
            if User.objects.filter(username=username).exists():
                username = f"{base_username}_{uuid.uuid4().hex[:6]}"
                
            user_username(user, username)
        return user
    
    def save_user(self, request, user, form, commit=True):
        """
        Saves a new user instance using information provided in the signup form.
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Ensure email is set
        email = form.cleaned_data.get('email')
        if email:
            user_email(user, email)
        
        # Populate username if needed
        user = self.populate_username(request, user)
        
        if commit:
            user.save()
        return user