from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.thing_list, name='thing_list'),
    path('things/', views.thing_list, name='thing_list'),
    path('things/create/', views.thing_create, name='thing_create'),
    path('things/<uuid:pk>/', views.thing_detail, name='thing_detail'),
    path('things/<uuid:pk>/edit/', views.thing_edit, name='thing_edit'),
    path('things/<uuid:pk>/delete/', views.thing_delete, name='thing_delete'),
] 