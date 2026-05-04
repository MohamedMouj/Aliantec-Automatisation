from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='listes_types'),
    path('download/<path:filename>/', views.download_file, name='download_zip'),
]
