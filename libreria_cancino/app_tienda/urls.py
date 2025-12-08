from django.urls import path
from . import views

app_name = 'app_tienda'

urlpatterns = [
    # Vistas Públicas
    path('', views.index, name='index'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('libro/<slug:slug>/', views.detalle_libro, name='detalle_libro'),
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('ofertas/', views.ofertas, name='ofertas'),
    path('contacto/', views.contacto, name='contacto'),

    # Vistas de Usuario Autenticado
    path('perfil/', views.perfil, name='perfil'),
    path('carrito/', views.carrito, name='carrito'),
    path('agregar-al-carrito/<int:libro_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('actualizar-carrito/', views.actualizar_carrito, name='actualizar_carrito'),
    path('checkout/', views.checkout, name='checkout'),
    path('proceso-pago/', views.proceso_pago, name='proceso_pago'),
    path('pago-exitoso/<str:numero_pedido>/', views.pago_exitoso, name='pago_exitoso'),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('mis-pedidos/<str:numero_pedido>/', views.detalle_pedido, name='detalle_pedido'),
    path('mis-descargas/', views.mis_descargas, name='mis_descargas'),
    path('descargar/<uuid:token>/', views.descargar_libro, name='descargar_libro'),

    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/agregar/<int:libro_id>/', views.agregar_wishlist, name='agregar_wishlist'),
    path('wishlist/eliminar/<int:libro_id>/', views.eliminar_wishlist, name='eliminar_wishlist'),

    # Webhook Stripe
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),

    # Vistas de Administración
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/pedidos/', views.admin_pedidos, name='admin_pedidos'),
    path('admin/pedidos/<str:numero_pedido>/', views.admin_detalle_pedido, name='admin_detalle_pedido'),
    path('admin/libros/', views.admin_libros, name='admin_libros'),
    path('admin/libros/crear/', views.admin_crear_libro, name='admin_crear_libro'),
    path('admin/libros/editar/<slug:slug>/', views.admin_editar_libro, name='admin_editar_libro'),
    path('admin/libros/eliminar/<slug:slug>/', views.admin_eliminar_libro, name='admin_eliminar_libro'),
    path('admin/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin/reportes/', views.admin_reportes, name='admin_reportes'),
]
