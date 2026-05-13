from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='extraction_vin'),
    path('download/', views.download_file, name='extraction_vin_download'),
]
