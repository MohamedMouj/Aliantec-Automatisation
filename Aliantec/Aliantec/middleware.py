from django.shortcuts import redirect
from django.urls import reverse

class GlobalAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path
            
            # Allow access to static media, admin, and the login page itself
            try:
                login_url = reverse('login')
            except Exception:
                login_url = '/login/'
                
            if not (
                path.startswith('/static/') or 
                path.startswith('/media/') or 
                path.startswith('/admin/') or 
                path == login_url
            ):
                return redirect('login')
        
        return self.get_response(request)
