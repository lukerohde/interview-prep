from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import view_application
from . import view_voice_chat
from . import view_flashcard

app_name = 'main'

# API Routes
api_router = DefaultRouter()
api_router.register(r'flashcards', view_flashcard.FlashCardViewSet, basename='api-flashcard')
api_router.register(r'applications', view_application.ApplicationViewSet, basename='api-application')
api_router.register(r'voice-chat', view_voice_chat.VoiceChatViewSet, basename='api-voice-chat')

api_patterns = [
    path('api/', include(api_router.urls)),
]

# View Routes
view_patterns = [
    path('', view_application.application_list, name='application_list'),
    path('applications/', include([
        path('', view_application.application_list, name='application_list'),
        path('create/', view_application.application_create, name='application_create'),
        path('<uuid:pk>/', view_application.application_detail, name='application_detail'),
        path('<uuid:pk>/edit/', view_application.application_edit, name='application_edit'),
        path('<uuid:pk>/delete/', view_application.application_delete, name='application_delete'),
    ])),
]

urlpatterns = api_patterns + view_patterns