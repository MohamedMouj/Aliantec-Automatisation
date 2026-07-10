from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dad_dag'),
    path('finalize/', views.finalize, name='dad_dag_finalize'),
]
