from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import deck_views
from .views import voice_chat_views
from .views import flashcard_views
from .views import document_views
from .views import tutor_views
from .views import user_views

app_name = 'main'

# API Routes
api_router = DefaultRouter()
api_router.register(r'decks/(?P<deck_pk>[^/.]+)/flashcards', flashcard_views.FlashCardViewSet, basename='api-flashcard')
api_router.register(r'tutors/(?P<url_path>[^/.]+)/decks', deck_views.DeckViewSet, basename='api-deck')
# Voice chat endpoints handled separately below
api_router.register(r'documents', document_views.DocumentViewSet, basename='api-document')

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
    path('invitations/', include([
        path('', user_views.list_invitations, name='invitation_list'),
        path('invite/', user_views.invite_user, name='invitation_form'),
        path('<uuid:invitation_id>/delete/', user_views.delete_invitation, name='invitation_delete'),
    ])),
]

urlpatterns = api_patterns + view_patterns