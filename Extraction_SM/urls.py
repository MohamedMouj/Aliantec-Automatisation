from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='extraction_sm'),
    path('download/', views.download_file, name='extraction_sm_download'),
]
