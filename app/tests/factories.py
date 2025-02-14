# tests/factories.py
import factory
from django.contrib.auth.models import User
from main.models import Thing

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

class ThingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Thing
    
    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Thing {n}")