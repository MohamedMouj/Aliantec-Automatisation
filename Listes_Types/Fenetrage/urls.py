from django.urls import path
from . import views

urlpatterns = [
    path('', views.fenetrage, name='fenetrage'),
    path('download/<path:filename>/', views.download_file, name='fenetrage_download'),
]
