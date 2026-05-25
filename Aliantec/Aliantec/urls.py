from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from Main import views as main_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', main_views.logout_view, name='logout'),
    path('', include('Main.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
