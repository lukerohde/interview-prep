from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import deck_views
from .views import voice_chat_views
from .views import flashcard_views
from .views import document_views
from .views import tutor_views
# from . import view_application
# from . import view_voice_chat
# from . import view_flashcard
# from . import view_text_ai_response


app_name = 'main'

# API Routes
api_router = DefaultRouter()
api_router.register(r'decks/(?P<deck_pk>[^/.]+)/flashcards', flashcard_views.FlashCardViewSet, basename='api-flashcard')
api_router.register(r'tutors/(?P<url_path>[^/.]+)/decks', deck_views.DeckViewSet, basename='api-deck')
# Voice chat endpoints handled separately below
api_router.register(r'documents', document_views.DocumentViewSet, basename='api-document')
# api_router.register(r'flashcards', view_flashcard.FlashCardViewSet, basename='api-flashcard')
# api_router.register(r'applications', view_application.ApplicationViewSet, basename='api-application')
# api_router.register(r'voice-chat', view_voice_chat.VoiceChatViewSet, basename='api-voice-chat')
# api_router.register(r'text-ai-response', view_text_ai_response.TextAIResponseViewSet, basename='text-ai-response')

api_patterns = [
    path('api/', include(api_router.urls)),
    path('api/tutors/<str:tutor_path>/voice-chat/session/', voice_chat_views.VoiceChatViewSet.as_view({'get': 'session'}), name='api-voice-chat-session'),
]

# View Routes
view_patterns = [
    path('', tutor_views.tutor_list, name='home'),  # Home page shows tutor list

    path('documents/', include([
        path('', document_views.document_list, name='document_list'),
        path('create/', document_views.document_create, name='document_create'),
        path('create/<uuid:deck_id>/', document_views.document_create, name='document_create_for_deck'),
        path('<uuid:pk>/', document_views.document_detail, name='document_detail'),
        path('<uuid:pk>/edit/', document_views.document_edit, name='document_edit'),
        path('<uuid:pk>/delete/', document_views.document_delete, name='document_delete'),
    ])),
    path('tutors/<str:url_path>/', include([
        path('prompts/', tutor_views.tutor_prompts, name='tutor_prompts'),
        path('prompts/update/', tutor_views.update_prompt_override, name='update_prompt_override'),
        path('decks/', deck_views.deck_list, name='deck_list'),
        path('decks/create/', deck_views.deck_create, name='deck_create'),
        path('decks/<uuid:pk>/', deck_views.deck_detail, name='deck_detail'),
        path('decks/<uuid:pk>/edit/', deck_views.deck_edit, name='deck_edit'),
        path('decks/<uuid:pk>/delete/', deck_views.deck_delete, name='deck_delete'),
    ])),
    # path('', view_application.application_list, name='application_list'),
    # path('applications/', include([
    #     path('', view_application.application_list, name='application_list'),
    #     path('create/', view_application.application_create, name='application_create'),
    #     path('<uuid:pk>/', view_application.application_detail, name='application_detail'),
    #     path('<uuid:pk>/edit/', view_application.application_edit, name='application_edit'),
    #     path('<uuid:pk>/delete/', view_application.application_delete, name='application_delete'),
    # ]))
]

urlpatterns = api_patterns + view_patterns
