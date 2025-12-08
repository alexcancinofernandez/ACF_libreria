from django.contrib import admin
from .models import *

class LibroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'categoria', 'precio', 'activo')

admin.site.register(Usuario)
admin.site.register(Categoria)
admin.site.register(Libro, LibroAdmin)
admin.site.register(CarritoItem)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(EntregaDigital)
admin.site.register(Resena)
admin.site.register(Wishlist)
admin.site.register(Cupon)
admin.site.register(HistorialPedido)