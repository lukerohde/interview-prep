from rest_framework import serializers
from .models import FlashCard

class FlashCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashCard
        fields = [
            'id', 'front', 'back', 'tags', 'applications', 'created_at', 'updated_at',
            'front_last_review', 'front_interval', 'front_review_count', 'front_easiness_factor', 'front_repetitions',
            'back_last_review', 'back_interval', 'back_review_count', 'back_easiness_factor', 'back_repetitions'
        ]
        read_only_fields = [
            'created_at', 'updated_at',
            'front_last_review', 'front_interval', 'front_review_count', 'front_easiness_factor', 'front_repetitions',
            'back_last_review', 'back_interval', 'back_review_count', 'back_easiness_factor', 'back_repetitions'
        ]
