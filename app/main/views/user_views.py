from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from main.models import Invitation
from main.forms import InvitationForm

def is_admin(user):
    """Check if user is an admin"""
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_admin)
def invite_user(request):
    """View for admins to invite new users"""
    invitation = None
    invite_url = None
    
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Check if invitation already exists
            existing_invitation = Invitation.objects.filter(email__iexact=email, accepted_at=None).first()
            if existing_invitation:
                invitation = existing_invitation
                messages.warning(request, f"An invitation for {email} already exists.")
            elif User.objects.filter(email__iexact=email).exists():
                messages.warning(request, f"A user with email {email} already exists.")
            else:
                # Create new invitation
                invitation = Invitation.objects.create(
                    email=email,
                    invited_by=request.user
                )
                messages.success(request, f"Invitation created for {email}.")
            
            # Generate invitation link
            if invitation:
                invite_url = request.build_absolute_uri(reverse('account_login') + f"?invitation_id={invitation.id}")
    else:
        form = InvitationForm()
        
    return render(request, 'main/invite_user.html', {
        'form': form,
        'invitation': invitation,
        'invite_url': invite_url
    })

@login_required
@user_passes_test(is_admin)
def list_invitations(request):
    """View for admins to see all invitations"""
    invitations = Invitation.objects.all().order_by('-created_at')
    
    # Generate invitation links for each invitation
    for invitation in invitations:
        invitation.invite_url = request.build_absolute_uri(reverse('account_login') + f"?invitation_id={invitation.id}")
        
    return render(request, 'main/list_invitations.html', {'invitations': invitations})

@login_required
@user_passes_test(is_admin)
def delete_invitation(request, invitation_id):
    """View for admins to delete an invitation"""
    invitation = get_object_or_404(Invitation, id=invitation_id)
    
    if request.method == 'POST':
        email = invitation.email
        
        # Check if the invitation has been accepted and disable the user if needed
        if invitation.is_accepted and invitation.accepted_by:
            user = invitation.accepted_by
            if not user.is_staff:  # Don't disable staff users
                user.is_active = False
                user.save()
                messages.success(request, f"User account for {email} has been disabled.")
        
        # Delete the invitation
        invitation.delete()
        messages.success(request, f"Invitation for {email} has been deleted.")
        
    return redirect('main:list_invitations')
