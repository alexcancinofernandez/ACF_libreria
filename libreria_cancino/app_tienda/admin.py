from django.contrib import admin
from .models import *

admin.site.register(Usuario)
admin.site.register(Categoria)
admin.site.register(Libro)
admin.site.register(CarritoItem)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(EntregaDigital)
admin.site.register(Resena)
admin.site.register(Wishlist)
admin.site.register(Cupon)
admin.site.register(HistorialPedido)
