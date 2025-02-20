from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.template.loader import render_to_string
from django.urls import reverse
from django.db.models import Q, F
from django.utils import timezone
from django.db import models
from random import choice
from .models import FlashCard, ReviewStatus
from .serializers import FlashCardSerializer

class FlashCardViewSet(viewsets.GenericViewSet,
                     viewsets.mixins.ListModelMixin,
                     viewsets.mixins.CreateModelMixin,
                     viewsets.mixins.DestroyModelMixin):
    serializer_class = FlashCardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return flashcards belonging to the current user, sorted by most recent review
        return FlashCard.objects.filter(user=self.request.user).order_by(
            models.F('front_last_review').desc(nulls_last=True),
            models.F('back_last_review').desc(nulls_last=True),
            '-created_at'
        )

    def update(self, request, pk=None):
        """Custom update that handles both user edits and AI updates"""
        try:
            # Get card from filtered queryset (404 if not found or not owned)
            card = self.get_queryset().get(pk=pk)
            
            # Validate and update
            serializer = self.get_serializer(card, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Get the review side and show_both from request if present
            review_side = request.query_params.get('reviewSide')
            show_both = request.query_params.get('show_both') == 'true'
            
            # Always render preview HTML
            preview_html = render_to_string('main/_flashcard_preview.html', {'flashcard': card})
            
            # Render review HTML only if we have review_side
            review_html = None
            if review_side:
                review_html = render_to_string('main/_flashcard_review.html', {
                    'card': card,
                    'side': review_side,
                    'show_both': show_both
                })
            
            return Response({
                'data': serializer.data,
                'preview_html': preview_html,
                'review_html': review_html
            })
            
        except FlashCard.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        html = render_to_string('main/_flashcard_preview.html', {
            'flashcards': queryset
        })
        return Response({
            'data': serializer.data,
            'html': html
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        serializer.save(user=self.request.user)
        
        # Handle both single item and list cases for getting IDs
        if isinstance(serializer.data, list):
            flashcard_ids = [item['id'] for item in serializer.data]
        else:
            flashcard_ids = [serializer.data['id']]

        # Get the flashcards and render the preview
        flashcards = FlashCard.objects.filter(id__in=flashcard_ids)
        html_parts = []
        for flashcard in flashcards:
            html_part = render_to_string('main/_flashcard_preview.html', {'flashcard': flashcard})
            html_parts.append(html_part)
        html = ''.join(html_parts)
        response_data = {
            'data': serializer.data,
            'html': html
        }

        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'])
    def next_review(self, request):
        """Get the next card due for review"""
        now = timezone.now()
        queryset = self.get_queryset()

        # Get the side to review
        side = request.query_params.get('reviewSide', 'either')
        
        # Get cards that need review (either never reviewed or due)
        review_needed = []
        unreviewed = []

        for card in queryset:
            # Check front side
            if side in ['front', 'either'] and card.is_due_for_review('front'):
                if not card.front_last_review:
                    unreviewed.append((card, 'front'))
                else:
                    review_needed.append((card, 'front'))

            # Check back side
            if side in ['back', 'either'] and card.is_due_for_review('back'):
                if not card.back_last_review:
                    unreviewed.append((card, 'back'))
                else:
                    review_needed.append((card, 'back'))

        # Prioritize cards that need review over unreviewed cards
        if review_needed:
            card, side = choice(review_needed)
        elif unreviewed:
            card, side = choice(unreviewed)
        else:
            return Response({
                'html': render_to_string('main/_flashcard_review.html', {'card': None})
            })

        # Get show_both parameter
        show_both = request.query_params.get('show_both') == 'true'

        # Render the review template
        html = render_to_string('main/_flashcard_review.html', {
            'card': card,
            'side': side,
            'show_both': show_both
        })

        return Response({'html': html})



    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Update review status for a card"""
        card = self.get_object()
        status = request.data.get('status')
        side = request.data.get('side', 'front')
        notes = request.data.get('notes')

        if status not in [s.value for s in ReviewStatus]:
            return Response(
                {'error': f'Invalid status. Must be one of: {[s.value for s in ReviewStatus]}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the review status
        card.update_review(ReviewStatus(status), side, notes)

        # Get the updated preview of the judged card
        updated_preview = render_to_string('main/_flashcard_preview.html', {'flashcard': card})

        # Get the next card
        show_both = request.query_params.get('show_both') == 'true'
        
        # Combine the responses
        return Response({
            'updated_preview': updated_preview,  # The updated preview of the judged card
            'updated_card_id': str(card.id)  # The ID of the updated card
        })
