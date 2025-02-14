from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.application_list, name='application_list'),
    path('applications/', views.application_list, name='application_list'),
    path('applications/create/', views.application_create, name='application_create'),
    path('applications/<uuid:pk>/', views.application_detail, name='application_detail'),
    path('applications/<uuid:pk>/edit/', views.application_edit, name='application_edit'),
    path('applications/<uuid:pk>/delete/', views.application_delete, name='application_delete'),
] 