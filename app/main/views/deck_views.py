from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from main.models import Deck, FlashCard, Tutor, Document
from main.forms import DeckForm, DocumentForm
from django.contrib import messages
from django.db import transaction
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging
from django.http import JsonResponse

# Configure logger
logger = logging.getLogger(__name__)

class DeckViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Deck.objects.all()

    def get_queryset(self):
        queryset = Deck.objects.filter(owner=self.request.user, tutor=self.request.tutor)
        return queryset

    def create(self, request, *args, **kwargs):
        deck_form = DeckForm(request.POST)
        if deck_form.is_valid():
            try:
                with transaction.atomic():
                    deck = deck_form.save(commit=False)
                    deck.owner = request.user
                    deck.tutor = request.tutor
                    deck.status = 'active'
                    deck.save()

                    # Process multiple document fields
                    for key, value in request.POST.items():
                        if key.endswith('_content'):
                            document_name_key = key.replace('_content', '_name')
                            document_name = request.POST.get(document_name_key, 'Unnamed Document')
                            Document.objects.create(
                                name=document_name,
                                content=value,
                                owner=request.user,
                                deck=deck
                            )

                    # Generate interview questions
                    try:
                        created_cards = deck.generate_and_save_flashcards()
                        messages.success(request, f"Deck created successfully with {len(created_cards)} interview questions!")
                    except Exception as e:
                        logger.error(f"Error generating questions: {str(e)}")
                        messages.warning(request, "Deck created, but there was an error generating interview questions.")

                return redirect('main:deck_detail', url_path=request.tutor.url_path, pk=deck.pk)
            except Exception as e:
                logger.error(f"Error creating deck: {str(e)}")
                messages.error(request, "There was an error creating your deck. Please try again.")
        else:
            messages.error(request, "There was an error with your form. Please correct the errors and try again.")

        presenter = request.tutor.presenter()
        return render(request, 'main/deck_form.html', {'deck_form': deck_form, 'tutor': request.tutor, 'presenter': presenter})

    def update(self, request, *args, **kwargs):
        deck = self.get_object()
        deck_form = DeckForm(request.POST, instance=deck)
        if deck_form.is_valid():
            try:
                with transaction.atomic():
                    deck = deck_form.save()

                    # Keep track of processed documents to handle deletions
                    processed_docs = set()

                    # Process multiple document fields
                    for key, value in request.POST.items():
                        if key.endswith('_content'):
                            document_name_key = key.replace('_content', '_name')
                            document_name = request.POST.get(document_name_key, 'Unnamed Document')
                            document_id_key = key.replace('_content', '_id')
                            document_id = request.POST.get(document_id_key)

                            if document_id:
                                # Update existing document
                                try:
                                    document = Document.objects.get(id=document_id, deck=deck, owner=request.user)
                                    document.content = value
                                    document.name = document_name
                                    document.save()
                                    processed_docs.add(document.id)
                                except Document.DoesNotExist:
                                    # If document doesn't exist, create new one
                                    document = Document.objects.create(
                                        name=document_name,
                                        content=value,
                                        owner=request.user,
                                        deck=deck
                                    )
                                    processed_docs.add(document.id)
                            else:
                                # Create new document
                                document = Document.objects.create(
                                    name=document_name,
                                    content=value,
                                    owner=request.user,
                                    deck=deck
                                )
                                processed_docs.add(document.id)

                    # Delete documents that were not in the form
                    deck.documents.exclude(id__in=processed_docs).delete()

                    # Generate and save flashcards
                    created_cards = deck.generate_and_save_flashcards()
                    if created_cards:
                        messages.success(request, f"Deck updated with {len(created_cards)} new flashcards!")
                    else:
                        messages.warning(request, "Deck updated, but no content was provided for flashcard generation.")

                return redirect('main:deck_detail', url_path=request.tutor.url_path, pk=deck.pk)
            except Exception as e:
                logger.error(f"Error updating deck: {str(e)}")
                messages.error(request, "There was an error updating your deck. Please try again.")
        else:
            messages.error(request, "There was an error with your form. Please correct the errors and try again.")

        return render(request, 'main/deck_form.html', {
            'form': deck_form,
            'deck': deck,
            'documents': deck.documents.all(),
            'tutor': request.tutor
        })

    @action(detail=True, methods=['post'])
    def generate_questions(self, request, pk=None, url_path=None):
        """Generate interview questions for a deck."""
        deck = self.get_object()
        message = None

        try:
            cards = deck.generate_and_save_flashcards()
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
            try:
                with transaction.atomic():
                    deck = form.save(commit=False)
                    deck.owner = request.user
                    deck.tutor = request.tutor
                    deck.status = 'active'
                    deck.save()

                    # Process multiple document fields
                    for key, value in request.POST.items():
                        if key.endswith('_content'):
                            document_name_key = key.replace('_content', '_name')
                            document_name = request.POST.get(document_name_key, 'Unnamed Document')
                            document = Document.objects.create(
                                name=document_name,
                                content=value,
                                owner=request.user,
                                deck=deck
                            )

                    # Generate interview questions
                    try:
                        created_cards = deck.generate_and_save_flashcards()
                        messages.success(request, f"Deck created successfully with {len(created_cards)} interview questions!")
                    except Exception as e:
                        logger.error(f"Error generating questions: {str(e)}")
                        messages.warning(request, "Deck created, but there was an error generating interview questions.")

                return redirect('main:deck_detail', url_path=request.tutor.url_path, pk=deck.pk)
            except Exception as e:
                logger.error(f"Error creating deck: {str(e)}")
                messages.error(request, "There was an error creating your deck. Please try again.")
    else:
        form = DeckForm()

    presenter = request.tutor.presenter()
    return render(request, 'main/deck_form.html', {'form': form, 'tutor': request.tutor, 'presenter': presenter})

@login_required
def deck_edit(request, url_path, pk):
    """Edit an existing deck"""
    deck = get_object_or_404(Deck, pk=pk, owner=request.user, tutor=request.tutor)
    documents = deck.documents.all()

    if request.method == 'POST':
        form = DeckForm(request.POST, instance=deck)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the deck first
                    deck = form.save()

                    # Process multiple document fields
                    for key, value in request.POST.items():
                        if key.endswith('_content'):
                            document_name_key = key.replace('_content', '_name')
                            document_name = request.POST.get(document_name_key, 'Unnamed Document')
                            document_id_key = key.replace('_content', '_id')
                            document_id = request.POST.get(document_id_key)

                            if document_id:
                                document = Document.objects.get(id=document_id)
                                if request.POST.get(f'document_{document_id}_delete'):
                                    document.delete()
                                else:
                                    document.content = value
                                    document.save()
                            else:
                                Document.objects.create(
                                    name=document_name,
                                    content=value,
                                    owner=request.user,
                                    deck=deck
                                )

                    # Generate and save flashcards
                    created_cards = deck.generate_and_save_flashcards()
                    if created_cards:
                        messages.success(request, f"Deck updated with {len(created_cards)} new flashcards!")
                    else:
                        messages.warning(request, "Deck updated, but no content was provided for flashcard generation.")
                return redirect('main:deck_detail', url_path=url_path, pk=deck.pk)

            except Exception as e:
                error_msg = f"Error generating questions: {str(e)}"
                messages.error(request, "Failed to generate interview questions. Please try again.")
                return render(request, 'main/deck_form.html', {
                    'form': form,  # Contains the user's POST data
                    'deck': deck,
                    'documents': documents,
                    'tutor': request.tutor,
                    'is_retry': True,
                    'error_message': error_msg
                })
    else:
        form = DeckForm(instance=deck)

    presenter = deck.tutor.presenter()
    return render(request, 'main/deck_form.html', {'form': form, 'documents': documents, 'deck': deck, 'tutor': request.tutor, 'presenter': presenter})

@login_required
def deck_delete(request, url_path, pk):
    deck = get_object_or_404(Deck, pk=pk, owner=request.user, tutor=request.tutor)
    if request.method == 'POST':
        deck.delete()
        messages.success(request, "Deck deleted successfully!")
        return redirect('main:deck_list', url_path=url_path)
    return render(request, 'main/deck_confirm_delete.html', {'deck': deck, 'tutor': request.tutor})

@login_required
def delete_document(request, deck_pk, document_id):
    """Delete a document via AJAX"""
    if request.method == 'DELETE':
        try:
            document = get_object_or_404(Document, id=document_id, deck_id=deck_pk, owner=request.user)
            document.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


