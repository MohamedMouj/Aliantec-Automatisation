from django.urls import path
from . import views

urlpatterns = [
    path('', views.projet_project, name='projet_project'),
    path('download/<path:filename>/', views.download_file, name='projet_project_download'),
]
