from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='main'),
    path('listes_types/', include('Listes_Types.urls')),
    # path('listes_types/', include('Listes_Types.urls')),
    # path('listes_types/', include('Listes_Types.urls')),
    # path('listes_types/', include('Listes_Types.urls')),
    # path('listes_types/', include('Listes_Types.urls')),

]
