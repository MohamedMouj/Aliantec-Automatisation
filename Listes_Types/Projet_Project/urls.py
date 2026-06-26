from django.urls import path
from . import views

urlpatterns = [
    path('', views.projet_project, name='projet_project'),
]
