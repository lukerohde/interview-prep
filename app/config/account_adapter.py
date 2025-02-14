from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter

class InviteOnlyAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        return True #'joining_shareable_link' in request.session
        
    def get_signup_redirect_url(self, request):
        return super().get_signup_redirect_url(request)