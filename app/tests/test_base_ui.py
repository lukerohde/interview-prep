import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.test import Client

class UITestBase:
    """Base class for UI tests with common setup methods."""
    
    def setup_user_session(self, page, user):
        """Set up a logged-in user session for the page."""
        client = Client()
        client.force_login(user)
        
        # Get session cookie
        response = client.get(reverse('main:home'))
        session_cookie = client.cookies['sessionid']
        
        # Get CSRF token
        from django.middleware.csrf import get_token
        csrf_token = get_token(response.wsgi_request)
        
        # Add session and CSRF cookies to the page context
        page.context.add_cookies([
            {
                'name': 'sessionid',
                'value': session_cookie.value,
                'domain': 'localhost',
                'path': '/',
            },
            {
                'name': 'csrftoken',
                'value': csrf_token,
                'domain': 'localhost',
                'path': '/',
            }
        ])
    
    def wait_for_toast(self, page, expected_text=None):
        """Wait for a toast notification and optionally verify its text."""
        toast = page.locator(".toast.bg-success").last
        print("Waiting for success toast...")
        toast.wait_for(state="visible")
        assert toast.is_visible()
        if expected_text:
            assert expected_text in toast.text_content()
        return toast
    
    def wait_for_page_load(self, page):
        """Wait for the page to fully load."""
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=2000)
