from django.urls import resolve
from .models import Tutor

class TutorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Try to get tutor from URL
        url_name = resolve(request.path_info).url_name
        url_path = resolve(request.path_info).kwargs.get('url_path')
        if url_path:
            # URL has a tutor path - try to get that specific tutor
            try:
                request.tutor = Tutor.objects.get(url_path=url_path)
            except Tutor.DoesNotExist:
                request.tutor = None
        else:
            # No tutor path - check if we have exactly one tutor
            tutor_count = Tutor.objects.count()
            if tutor_count == 1:
                request.tutor = Tutor.objects.first()
            else:
                request.tutor = None

        response = self.get_response(request)
        return response
