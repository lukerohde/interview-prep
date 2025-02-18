from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import mimetypes
import logging
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Document, Deck
from ..forms import DocumentForm

logger = logging.getLogger(__name__)

class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Document.objects.filter(owner=self.request.user)
        
        # Filter by document type
        doc_type = self.request.query_params.get('type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
            
        # Filter by deck
        deck_id = self.request.query_params.get('deck')
        if deck_id:
            queryset = queryset.filter(decks__id=deck_id)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        """Handle file upload and content extraction."""
        document = self.get_object()
        file = request.FILES.get('file')
        
        if not file:
            return Response({'error': 'No file provided'}, status=400)
            
        # Save the file
        file_path = default_storage.save(f'documents/{file.name}', ContentFile(file.read()))
        document.url = file_path
        
        # TODO: Extract text content from file based on type
        # For now, just use the file name as content
        document.content = f"Content from {file.name}"
        document.save()
        
        return Response({'status': 'success', 'url': document.url})

@login_required
def document_list(request):
    documents = Document.objects.filter(owner=request.user)
    
    # Filter by document type
    doc_type = request.GET.get('type')
    if doc_type:
        documents = documents.filter(document_type=doc_type)
        
    # Filter by deck
    deck_id = request.GET.get('deck')
    if deck_id:
        documents = documents.filter(decks__id=deck_id)
    
    # Get available document types for filter dropdown
    document_types = Document.DocumentType.choices
    
    # Get user's decks for filter dropdown
    decks = Deck.objects.filter(owner=request.user)
    
    documents = documents.order_by('-created_at')
    
    return render(request, 'main/document_list.html', {
        'documents': documents,
        'document_types': document_types,
        'decks': decks,
        'current_type': doc_type,
        'current_deck': deck_id
    })

@login_required
def document_create(request, deck_id=None):
    deck = None
    if deck_id:
        deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.owner = request.user
            
            # Handle file upload if provided
            if 'file' in request.FILES:
                file = request.FILES['file']
                file_path = default_storage.save(f'documents/{file.name}', ContentFile(file.read()))
                document.url = file_path
                
                # TODO: Extract text content from file based on type
                # For now, just use the form content or file name
                if not document.content:
                    document.content = f"Content from {file.name}"
            
            document.save()
            
            # Add to deck if specified
            if deck:
                deck.documents.add(document)
            
            return redirect('main:document_detail', pk=document.id)
    else:
        form = DocumentForm()
    
    return render(request, 'main/document_form.html', {
        'form': form,
        'deck': deck
    })

@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document, id=pk, owner=request.user)
    return render(request, 'main/document_detail.html', {
        'document': document
    })

@login_required
def document_edit(request, pk):
    document = get_object_or_404(Document, id=pk, owner=request.user)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            document = form.save()
            
            # Handle file upload if provided
            if 'file' in request.FILES:
                # Delete old file if it exists
                if document.url:
                    try:
                        default_storage.delete(document.url)
                    except Exception as e:
                        logger.error(f"Error deleting old file: {e}")
                
                file = request.FILES['file']
                file_path = default_storage.save(f'documents/{file.name}', ContentFile(file.read()))
                document.url = file_path
                document.save()
            
            return redirect('main:document_detail', pk=document.id)
    else:
        form = DocumentForm(instance=document)
    
    return render(request, 'main/document_form.html', {
        'form': form,
        'document': document
    })

@login_required
@require_http_methods(["POST"])
def document_delete(request, pk):
    document = get_object_or_404(Document, id=pk, owner=request.user)
    
    # Delete file if it exists
    if document.url:
        try:
            default_storage.delete(document.url)
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
    
    document.delete()
    return JsonResponse({'status': 'success'})
