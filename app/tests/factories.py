# tests/factories.py
import factory
from django.contrib.auth.models import User
from main.models import Deck, FlashCard, Tutor, Invitation
from django.utils import timezone

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True  # Prevents the automatic save after set_password

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall('set_password', 'password123')
    is_staff = False
    is_superuser = False
    is_active = True

    @factory.post_generation
    def password_save(obj, create, extracted, **kwargs):
        if create:
            obj.save()

class TutorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tutor
        django_get_or_create = ('url_path',)
    
    name = factory.Sequence(lambda n: f"Test Tutor {n}")
    deck_name = factory.Sequence(lambda n: f"Test Tutor Decks")
    url_path = factory.Sequence(lambda n: f"test-tutor-{n}")
    config_path = factory.Sequence(lambda n: f"tutors/test_tutor_{n}.yaml")

class DeckFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Deck
    
    owner = factory.SubFactory(UserFactory)
    tutor = factory.SubFactory(TutorFactory)
    name = factory.Sequence(lambda n: f"Study Deck {n}")
    status = 'active'
    deck_type = Deck.DeckType.STUDY

class FlashcardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FlashCard
        skip_postgeneration_save = True  # Prevents the automatic save after postgeneration

    user = factory.SubFactory(UserFactory)
    front = factory.Sequence(lambda n: f"Question {n}")
    back = factory.Sequence(lambda n: f"Answer {n}")
    front_last_review = None
    back_last_review = None
    tags = ['test']

    @factory.post_generation
    def save_flashcard(obj, create, extracted, **kwargs):
        if create:
            obj.save()


    @factory.post_generation
    def decks(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for deck in extracted:
                self.decks.add(deck)
        self.save()

class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation
    
    email = factory.Sequence(lambda n: f"invited{n}@example.com")
    invited_by = factory.SubFactory(UserFactory, is_staff=True)
    created_at = factory.LazyFunction(timezone.now)
    accepted_at = None
    accepted_by = None