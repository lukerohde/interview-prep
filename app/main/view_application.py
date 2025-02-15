from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Application, FlashCard
from .forms import ApplicationForm
from .serializers import FlashCardSerializer

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

class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Application.objects.filter(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def generate_questions(self, request, pk=None):
        """Generate interview questions for an application."""
        application = self.get_object()
        message = None
        
        try:
            cards = application.generate_and_save_questions()
            message = f'Generated {len(cards)} new questions!'
        except Exception as e:
            logger.error(f'Error generating questions: {str(e)}')
            message = 'Failed to generate questions'
            
        if 'text/html' in request.headers.get('Accept', ''):
            messages.success(request, message) if 'Generated' in message else messages.error(request, message)
            return redirect('main:application_detail', pk=application.pk)
            
        return Response({'message': message}, status=status.HTTP_200_OK if 'Generated' in message else status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
def application_list(request):
    applications = Application.objects.filter(owner=request.user)
    if not applications.exists():
        messages.info(request, "Create your first job application!")
        return redirect('main:application_create')
    return render(request, 'main/application_list.html', {'applications': applications})

@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk, owner=request.user)
    flashcards = application.flashcards.all()
    return render(request, 'main/application_detail.html', {
        'application': application,
        'flashcards': flashcards
    })

@login_required
def application_create(request):
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                application = form.save(commit=False)
                application.owner = request.user
                application.save()
                
                # Generate interview questions
                try:
                    created_cards = application.generate_and_save_questions()
                    messages.success(request, f"Application created successfully with {len(created_cards)} interview questions!")
                except Exception as e:
                    logger.error(f"Error generating questions: {str(e)}")
                    messages.warning(request, "Application created, but there was an error generating interview questions.")
                
            return redirect('main:application_detail', pk=application.pk)
    else:
        form = ApplicationForm()
    return render(request, 'main/application_form.html', {'form': form})

@login_required
def application_edit(request, pk):
    """Edit an existing application"""
    application = get_object_or_404(Application, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, instance=application)
        if form.is_valid():
            with transaction.atomic():
                application = form.save()
                
                # Generate new questions
                try:
                    created_cards = application.generate_and_save_questions()
                    messages.success(request, f"Application updated with {len(created_cards)} new interview questions!")
                except Exception as e:
                    logger.error(f"Error generating questions: {str(e)}")
                    messages.warning(request, "Application updated, but there was an error generating new interview questions.")
                
            return redirect('main:application_detail', pk=application.pk)
    else:
        form = ApplicationForm(instance=application)
    
    return render(request, 'main/application_form.html', {'form': form, 'application': application})

@login_required
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk, owner=request.user)
    if request.method == 'POST':
        application.delete()
        messages.success(request, "Application deleted successfully!")
        return redirect('main:application_list')
    return render(request, 'main/application_confirm_delete.html', {'application': application})


