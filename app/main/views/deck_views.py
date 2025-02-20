from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from main.models import Deck, FlashCard, Tutor
from main.forms import DeckForm
from main.serializers import FlashCardSerializer

import requests
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.db import transaction
from collections import defaultdict
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import JsonResponse
import logging
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
            
# from django.contrib.auth import login

# Configure logger
logger = logging.getLogger(__name__)

class DeckViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Deck.objects.filter(owner=self.request.user, tutor=self.request.tutor)
        return queryset
    
    @action(detail=True, methods=['post'])
    def generate_questions(self, request, pk=None, url_path=None):
        """Generate interview questions for a deck."""
        deck = self.get_object()
        message = None
        
        try:
            cards = deck.generate_and_save_questions()
            message = f'Generated {len(cards)} new questions!'
        except Exception as e:
            logger.error(f'Error generating questions: {str(e)}')
            message = 'Failed to generate questions'
            
        if 'text/html' in request.headers.get('Accept', ''):
            messages.success(request, message) if 'Generated' in message else messages.error(request, message)
            return redirect('main:deck_detail', url_path=url_path, pk=deck.pk)
            
        return Response({'message': message}, status=status.HTTP_200_OK if 'Generated' in message else status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
def deck_list(request, url_path):
    decks = Deck.objects.filter(owner=request.user, tutor=request.tutor)
    if not decks.exists():
        return redirect('main:deck_create', url_path=url_path)
    return render(request, 'main/deck_list.html', {'decks': decks, 'tutor': request.tutor})

@login_required
def deck_detail(request, url_path, pk):
    deck = get_object_or_404(Deck, pk=pk, owner=request.user, tutor=request.tutor)
    flashcards = deck.flashcards.all()
    return render(request, 'main/deck_detail.html', {
        'deck': deck,
        'flashcards': flashcards,
        'tutor': request.tutor
    })

@login_required
def deck_create(request, url_path):
    if request.method == 'POST':
        form = DeckForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                deck = form.save(commit=False)
                deck.owner = request.user
                deck.tutor = request.tutor
                deck.save()
                
                # Generate interview questions
                try:
                    created_cards = deck.generate_and_save_questions()
                    messages.success(request, f"Deck created successfully with {len(created_cards)} interview questions!")
                except Exception as e:
                    logger.error(f"Error generating questions: {str(e)}")
                    messages.warning(request, "Deck created, but there was an error generating interview questions.")
                
            return redirect('main:deck_detail', url_path=request.tutor.url_path, pk=deck.pk)
    else:
        form = DeckForm()
    return render(request, 'main/deck_form.html', {'form': form, 'tutor': request.tutor})

def deck_edit(request, url_path, pk):
    """Edit an existing deck"""
    deck = get_object_or_404(Deck, pk=pk, owner=request.user, tutor=request.tutor)
    
    if request.method == 'POST':
        form = DeckForm(request.POST, instance=deck)
        if form.is_valid():
            with transaction.atomic():
                deck = form.save()
                
                # Generate new questions
                try:
                    created_cards = deck.generate_and_save_questions()
                    messages.success(request, f"Deck updated with {len(created_cards)} new interview questions!")
                except Exception as e:
                    logger.error(f"Error generating questions: {str(e)}")
                    messages.warning(request, "Deck updated, but there was an error generating new interview questions.")
                
            return redirect('main:deck_detail', url_path=url_path, pk=deck.pk)
    else:
        form = DeckForm(instance=deck)
    
    return render(request, 'main/deck_form.html', {'form': form, 'deck': deck, 'tutor': request.tutor})
    
def deck_delete(request, url_path, pk):
    deck = get_object_or_404(Deck, pk=pk, owner=request.user, tutor=request.tutor)
    if request.method == 'POST':
        deck.delete()
        messages.success(request, "Deck deleted successfully!")
        return redirect('main:deck_list', url_path=url_path)
    return render(request, 'main/deck_confirm_delete.html', {'deck': deck, 'tutor': request.tutor})


