from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Application, FlashCard
from .forms import ApplicationForm
import requests
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.db import transaction
from collections import defaultdict
from django.http import HttpResponseRedirect
from django.urls import reverse
from .ai_helpers import call_openai, generate_interview_questions
import logging
# from django.contrib.auth import login

# Configure logger
logger = logging.getLogger(__name__)

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
    return render(request, 'main/application_detail.html', {'application': application})

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
                    questions = generate_interview_questions(
                        job_description=application.job_description,
                        resume=application.resume
                    )
                    
                    # Create flashcards from generated questions
                    for q in questions:
                        flashcard = FlashCard.objects.create(
                            user=request.user,
                            front=q['question'],
                            back=q['suggested_answer'],
                            tags=[q['category'], 'auto-generated']
                        )
                        flashcard.applications.add(application)
                    
                    messages.success(request, f"Application created successfully with {len(questions)} interview questions!")
                except Exception as e:
                    logger.error(f"Error generating questions: {str(e)}")
                    messages.warning(request, "Application created, but there was an error generating interview questions.")
                
            return redirect('main:application_detail', pk=application.pk)
    else:
        form = ApplicationForm()
    return render(request, 'main/application_form.html', {'form': form})

@login_required
def application_edit(request, pk):
    application = get_object_or_404(Application, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ApplicationForm(request.POST, instance=application)
        if form.is_valid():
            with transaction.atomic():
                application = form.save()
                
                # Get existing questions to avoid duplicates
                existing_questions = [
                    {'question': card.front, 'suggested_answer': card.back}
                    for card in application.flashcards.filter(tags__contains=['auto-generated'])
                ]
                
                # Generate new questions
                try:
                    questions = generate_interview_questions(
                        job_description=application.job_description,
                        resume=application.resume,
                        existing_questions=existing_questions
                    )
                    
                    # Create flashcards from generated questions
                    for q in questions:
                        flashcard = FlashCard.objects.create(
                            user=request.user,
                            front=q['question'],
                            back=q['suggested_answer'],
                            tags=[q['category'], 'auto-generated']
                        )
                        flashcard.applications.add(application)
                    
                    messages.success(request, f"Application updated with {len(questions)} new interview questions!")
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
