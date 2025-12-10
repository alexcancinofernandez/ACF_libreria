
from django.shortcuts import redirect
from django.urls import reverse

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if not request.user.is_authenticated or not request.user.es_administrador():
                return redirect(reverse('app_tienda:login_view') + '?next=' + request.path)
        
        response = self.get_response(request)
        return response
