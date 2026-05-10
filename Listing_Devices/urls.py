from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='main'),
    path('device-listing/', views.index, name='device_listing'),

]
