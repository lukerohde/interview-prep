from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Application
from .forms import ApplicationForm
import requests
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.db import transaction
from collections import defaultdict
from django.http import HttpResponseRedirect
from django.urls import reverse
from .ai_helpers import call_openai
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
            application = form.save(commit=False)
            application.owner = request.user
            application.save()
            messages.success(request, "Application created successfully!")
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
            form.save()
            messages.success(request, "Application updated successfully!")
            return redirect('main:application_detail', pk=application.pk)
    else:
        form = ApplicationForm(instance=application)
    return render(request, 'main/application_form.html', {'form': form})

@login_required
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk, owner=request.user)
    if request.method == 'POST':
        application.delete()
        messages.success(request, "Application deleted successfully!")
        return redirect('main:application_list')
    return render(request, 'main/application_confirm_delete.html', {'application': application})
