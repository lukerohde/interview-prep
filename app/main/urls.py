from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import deck_views
from .views import voice_chat_views
from .views import flashcard_views
from .views import document_views
from .views import tutor_views

app_name = 'main'

# API Routes
api_router = DefaultRouter()
api_router.register(r'flashcards', flashcard_views.FlashCardViewSet, basename='api-flashcard')
api_router.register(r'decks', deck_views.DeckViewSet, basename='api-deck')
api_router.register(r'tutors/(?P<url_path>[\w-]+)/voice-chat', voice_chat_views.VoiceChatViewSet, basename='api-voice-chat')
api_router.register(r'documents', document_views.DocumentViewSet, basename='api-document')

api_patterns = [
    path('api/', include(api_router.urls)),
]

# View Routes
view_patterns = [
    path('', deck_views.deck_list, name='home'),  # Home page shows deck list
    path('tutors/', include([
        path('<str:url_path>/prompts/', tutor_views.tutor_prompts, name='tutor_prompts'),
        path('<str:url_path>/prompts/update/', tutor_views.update_prompt_override, name='update_prompt_override'),
    ])),
    path('documents/', include([
        path('', document_views.document_list, name='document_list'),  # Fixed: now points to document_list view
        path('create/', document_views.document_create, name='document_create'),
        path('create/<uuid:deck_id>/', document_views.document_create, name='document_create_for_deck'),
        path('<uuid:pk>/', document_views.document_detail, name='document_detail'),
        path('<uuid:pk>/edit/', document_views.document_edit, name='document_edit'),
        path('<uuid:pk>/delete/', document_views.document_delete, name='document_delete'),
    ])),
    path('decks/', include([
        path('', deck_views.deck_list, name='deck_list'),
        path('create/', deck_views.deck_create, name='deck_create'),
        path('<uuid:pk>/', deck_views.deck_detail, name='deck_detail'),
        path('<uuid:pk>/edit/', deck_views.deck_edit, name='deck_edit'),
        path('<uuid:pk>/delete/', deck_views.deck_delete, name='deck_delete'),
    ])),
]

urlpatterns = api_patterns + view_patterns