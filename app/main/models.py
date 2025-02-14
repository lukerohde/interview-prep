from django.db import models
from django.contrib.auth.models import User
from .utils import do_something_handy
from uuid import uuid4

class Thing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_things')

    def __str__(self):
        return self.name

# class SubThing(models.Model):
#     thing = models.ForeignKey(Thing, on_delete=models.CASCADE, related_name='sub_thing_name')

