from django.urls import path
from . import view_application

app_name = 'main'

urlpatterns = [
    path('', view_application.application_list, name='application_list'),
    path('applications/', view_application.application_list, name='application_list'),
    path('applications/create/', view_application.application_create, name='application_create'),
    path('applications/<uuid:pk>/', view_application.application_detail, name='application_detail'),
    path('applications/<uuid:pk>/edit/', view_application.application_edit, name='application_edit'),
    path('applications/<uuid:pk>/delete/', view_application.application_delete, name='application_delete'),
] 