from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from allauth.account.forms import LoginForm
from allauth.account.utils import perform_login, user_username, user_email
from allauth.account import app_settings
from allauth.exceptions import ImmediateHttpResponse
import uuid

class MergedLoginSignupView:
    """
    A view that handles both login and signup in one form.
    If the user exists, they will be logged in.
    If the user doesn't exist, a new account will be created.
    """
    
    def __init__(self, request):
        self.request = request
        self.user = None
        self.form = LoginForm(request.POST or None)
        
    def process(self):
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
                    email_verification=app_settings.EMAIL_VERIFICATION,
                    redirect_url=app_settings.LOGIN_REDIRECT_URL
                )
            except ImmediateHttpResponse as e:
                return e.response
        else:
            # Invalid password
            messages.error(self.request, "Invalid password for this email.")
            return render(self.request, 'account/login.html', {'form': self.form})
    
    def _handle_signup(self, email, password):
        """Create a new user account"""
        try:
            # Generate a unique username if required
            username = None
            if app_settings.USER_MODEL_USERNAME_FIELD:
                # Try using the part before @ in the email
                base_username = email.split('@')[0]
                username = base_username
                
                # If username already exists, add a random suffix
                if User.objects.filter(username=username).exists():
                    username = f"{base_username}_{uuid.uuid4().hex[:8]}"
            
            # Create user with appropriate username handling
            user_kwargs = {
                'email': email,
                'password': password,
            }
            
            if username is not None:
                user_kwargs['username'] = username
                
            user = User.objects.create_user(**user_kwargs)
            
            # Log the user in
            try:
                return perform_login(
                    self.request, user,
                    email_verification=app_settings.EMAIL_VERIFICATION,
                    redirect_url=app_settings.LOGIN_REDIRECT_URL
                )
            except ImmediateHttpResponse as e:
                return e.response
                
        except Exception as e:
            messages.error(self.request, f"Error creating account: {str(e)}")
            return render(self.request, 'account/login.html', {'form': self.form})
