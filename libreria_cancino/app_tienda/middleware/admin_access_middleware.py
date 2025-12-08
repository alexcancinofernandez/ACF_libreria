from django.urls import reverse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

class AdminAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith(reverse('app_tienda:admin_dashboard')):
            if not (request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'tipo_usuario', '') == 'administrador')):
                return redirect('app_tienda:login')
