def generic_context(request):
    return {
        'project_name': 'Your Project Name',
        'current_user': request.user,
        # ... other generic context variables ...
    } 