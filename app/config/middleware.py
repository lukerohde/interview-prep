from django.shortcuts import redirect
from django.urls import reverse

class RedirectSignupToLoginMiddleware:
    """
    Middleware to redirect users from the signup page to the login page.
    This ensures that even if there are direct links to the signup page,
    users will be redirected to our merged login/signup page.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Get the path
        path = request.path
        
        # If this is the signup page, redirect to login
        if path == reverse('account_signup'):
            return redirect('account_login')
            
        # Otherwise, continue with the request
        return self.get_response(request)
