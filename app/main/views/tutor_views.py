from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Tutor, TutorPromptOverride

@login_required
def tutor_list(request):
    tutors = Tutor.objects.all()
    return render(request, 'main/tutor_list.html', {'tutors': tutors})

@login_required
def tutor_prompts(request, url_path):
    tutor = get_object_or_404(Tutor, url_path=url_path)
    config = tutor.get_config()
    
    # Get whitelist and current overrides
    whitelist = config.get('prompt-override-whitelist', [])
    overrides = {
        override.key: override.value 
        for override in request.user.prompt_overrides.filter(tutor_url_path=url_path)
    }
    
    # Extract default values for whitelisted paths
    defaults = {}
    for path in whitelist:
        value = config
        for key in path.split('.'):
            value = value.get(key, {})
        if isinstance(value, (str, int, float, bool)):
            defaults[path] = value
    
    context = {
        'tutor': tutor,
        'whitelist': whitelist,
        'defaults': defaults,
        'overrides': overrides
    }
    return render(request, 'main/tutor_prompts.html', context)

@login_required
@require_http_methods(["POST"])
def update_prompt_override(request, url_path):
    key = request.POST.get('key')
    value = request.POST.get('value', '').strip()
    
    tutor = get_object_or_404(Tutor, url_path=url_path)
    config = tutor.get_config()
    
    whitelist = config.get('prompt-override-whitelist', [])
    if key not in whitelist:
        return JsonResponse({'error': 'Invalid override key'}, status=400)
    
    # If value is empty, delete the override to revert to default
    if not value:
        TutorPromptOverride.objects.filter(
            user=request.user,
            tutor_url_path=url_path,
            key=key
        ).delete()
        return JsonResponse({'status': 'deleted'})
    
    # Update or create the override
    override, created = TutorPromptOverride.objects.update_or_create(
        user=request.user,
        tutor_url_path=url_path,
        key=key,
        defaults={'value': value}
    )
    
    return JsonResponse({'status': 'updated' if not created else 'created'})
