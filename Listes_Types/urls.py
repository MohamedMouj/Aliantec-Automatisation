from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='DAD_DAG'),
    path('download/<path:filename>/', views.download_file, name='download_zip'),
]
