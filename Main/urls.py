from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='main'),
    path('listes_types/', include('Listes_Types.urls')),
    path('FSCFAI_Compare/', include('FSCFAI_Compare.urls')),
    path('Listing_Devices/', include('Listing_Devices.urls')),
    path('ExtractionVIN/', include('ExtractionVIN.urls')),
    path('Extraction_SM/', include('Extraction_SM.urls')),
    # path('listes_types/', include('Listes_Types.urls')),
    # path('listes_types/', include('Listes_Types.urls')),

]
