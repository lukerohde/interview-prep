class DefaultApplication:
    def __init__(self):
        self.title = 'Job Applications'  # Default title when no application is selected

def generic_context(request):
    return {
        'project_name': 'Your Project Name',
        'current_user': request.user,
        'application': DefaultApplication(),  # Provides a default application object
    }