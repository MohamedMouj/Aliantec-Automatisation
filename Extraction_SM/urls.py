from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='extraction_sm'),
    # download/ route removed — file is now streamed directly from the index view
]
