from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='listes_types_main'),
    path('fenetrage/', include('Listes_Types.Fenetrage.urls')),
    path('dad_dag/', include('Listes_Types.DAD_DAG.urls')),
    path('projet_project/', include('Listes_Types.Projet_Project.urls')),
]

