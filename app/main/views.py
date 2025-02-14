from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Thing
from .forms import ThingForm
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
def thing_list(request):
    things = Thing.objects.filter(owner=request.user)
    return render(request, 'main/thing_list.html', {'things': things})

@login_required
def thing_detail(request, pk):
    thing = get_object_or_404(Thing, pk=pk, owner=request.user)
    return render(request, 'main/thing_detail.html', {'thing': thing})

@login_required
def thing_create(request):
    if request.method == 'POST':
        form = ThingForm(request.POST)
        if form.is_valid():
            thing = form.save(commit=False)
            thing.owner = request.user
            thing.save()
            messages.success(request, "Thing created successfully!")
            return redirect('main:thing_detail', pk=thing.pk)
    else:
        form = ThingForm()
    return render(request, 'main/thing_form.html', {'form': form})

@login_required
def thing_edit(request, pk):
    thing = get_object_or_404(Thing, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ThingForm(request.POST, instance=thing)
        if form.is_valid():
            form.save()
            messages.success(request, "Thing updated successfully!")
            return redirect('main:thing_detail', pk=thing.pk)
    else:
        form = ThingForm(instance=thing)
    return render(request, 'main/thing_form.html', {'form': form})

@login_required
def thing_delete(request, pk):
    thing = get_object_or_404(Thing, pk=pk, owner=request.user)
    if request.method == 'POST':
        thing.delete()
        messages.success(request, "Thing deleted successfully!")
        return redirect('main:thing_list')
    return render(request, 'main/thing_confirm_delete.html', {'thing': thing})
