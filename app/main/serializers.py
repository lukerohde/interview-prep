from rest_framework import serializers
from .models import FlashCard

class FlashCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashCard
        fields = ['id', 'front', 'back', 'tags', 'applications', 'created_at', 'updated_at', 'last_reviewed_at', 'review_status']
        read_only_fields = ['created_at', 'updated_at', 'last_reviewed_at']
