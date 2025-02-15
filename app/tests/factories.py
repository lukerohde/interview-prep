# tests/factories.py
import factory
from django.contrib.auth.models import User
from main.models import Application, FlashCard
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

class ApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Application
    
    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Software Engineer {n}")
    status = 'draft'
    resume = factory.Sequence(lambda n: f"Resume content for application {n}")
    job_description = factory.Sequence(lambda n: f"Job description for position {n}")

class FlashcardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FlashCard

    user = factory.SubFactory(UserFactory)
    front = factory.Sequence(lambda n: f"Question {n}")
    back = factory.Sequence(lambda n: f"Answer {n}")
    front_last_review = None
    back_last_review = None
    tags = ['test']

    @factory.post_generation
    def applications(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for application in extracted:
                self.applications.add(application)