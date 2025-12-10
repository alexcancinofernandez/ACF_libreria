
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from app_tienda.models import (
    Usuario, Categoria, Libro, CarritoItem, Pedido, DetallePedido,
    EntregaDigital, Resena, Wishlist, Cupon, HistorialPedido
)

class Command(BaseCommand):
    help = 'Populate the database with a complete set of 10 records for each model.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting database population...")

        # Clean slate (optional, but good for testing)
        self.stdout.write("Deleting old data...")
        HistorialPedido.objects.all().delete()
        EntregaDigital.objects.all().delete()
        DetallePedido.objects.all().delete()
        Pedido.objects.all().delete()
        Resena.objects.all().delete()
        Wishlist.objects.all().delete()
        Cupon.objects.all().delete()
        CarritoItem.objects.all().delete()
        Libro.objects.all().delete()
        Categoria.objects.all().delete()
        Usuario.objects.filter(is_superuser=False).delete()


        # --- 1. Create Usuarios ---
        self.stdout.write("Creating 10 Usuarios...")
        usuarios = []
        for i in range(10):
            user, _ = Usuario.objects.get_or_create(
                username=f'cliente{i}',
                email=f'cliente{i}@example.com',
                defaults={
                    'first_name': f'Nombre{i}',
                    'last_name': f'Apellido{i}',
                    'password': make_password('password123'),
                    'tipo_usuario': 'cliente',
                    'telefono': f'12345678{i}',
                    'email_verificado': True,
                }
            )
            usuarios.append(user)
        self.stdout.write(self.style.SUCCESS("Usuarios created."))

        # --- 2. Create Categorias & Libros (50% on offer) ---
        self.stdout.write("Creating 4 Categorias and 10 Libros (5 on offer)...")
        cat_hipnosis, _ = Categoria.objects.get_or_create(nombre='Hipnosis', defaults={'descripcion': 'Libros sobre hipnosis.'})
        cat_religion, _ = Categoria.objects.get_or_create(nombre='Religión', defaults={'descripcion': 'Libros sobre religión.'})
        cat_desarrollo, _ = Categoria.objects.get_or_create(nombre='Desarrollo Personal', defaults={'descripcion': 'Libros de autoayuda.'})
        cat_poder, _ = Categoria.objects.get_or_create(nombre='Poder', defaults={'descripcion': 'Libros sobre poder e influencia.'})
        categorias = [cat_hipnosis, cat_religion, cat_desarrollo, cat_poder]

        titulos_autores = [
            ("El Poder de la Mente Subconsciente", "Joseph Murphy"),
            ("Trances Terapéuticos", "Stephen G. Gilligan"),
            ("La Biblia", "Varios"),
            ("El Corán", "Varios"),
            ("Piense y Hágase Rico", "Napoleón Hill"),
            ("Los 7 Hábitos de la Gente Altamente Efectiva", "Stephen Covey"),
            ("El Arte de la Guerra", "Sun Tzu"),
            ("Las 48 Leyes del Poder", "Robert Greene"),
            ("Meditaciones", "Marco Aurelio"),
            ("El Kybalión", "Tres Iniciados")
        ]
        
        libros = []
        for i, (titulo, autor) in enumerate(titulos_autores):
            precio_original = Decimal(random.uniform(15.99, 59.99)).quantize(Decimal('0.01'))
            en_oferta = (i % 2 == 0) # Make half of the books on offer
            precio_descuento = None
            if en_oferta:
                descuento = Decimal(random.uniform(0.2, 0.5)) # 20% to 50% off
                precio_descuento = (precio_original * (1 - descuento)).quantize(Decimal('0.01'))

            libro, _ = Libro.objects.get_or_create(
                titulo=titulo,
                defaults={
                    'autor': autor,
                    'categoria': random.choice(categorias),
                    'descripcion': f'Descripción detallada de {titulo}.',
                    'precio': precio_original,
                    'en_oferta': en_oferta,
                    'precio_descuento': precio_descuento,
                    'archivo_digital': 'libros_digitales/default.pdf',
                    'portada': 'portadas/default.jpg',
                    'paginas': random.randint(150, 500),
                    'isbn': f'978-0-00-{random.randint(100000, 999999)}-{i}',
                    'creado_por': random.choice(usuarios)
                }
            )
            libros.append(libro)
        self.stdout.write(self.style.SUCCESS("Categorias and Libros created."))

        # --- 3. Create Wishlists ---
        self.stdout.write("Creating 10 Wishlist items...")
        used_pairs = set()
        for _ in range(10):
            usuario = random.choice(usuarios)
            libro = random.choice(libros)
            if (usuario, libro) not in used_pairs:
                Wishlist.objects.create(usuario=usuario, libro=libro)
                used_pairs.add((usuario, libro))
        self.stdout.write(self.style.SUCCESS("Wishlist items created."))

        # --- 4. Create Carrito Items ---
        self.stdout.write("Creating 10 Carrito items...")
        used_pairs = set()
        for _ in range(10):
            usuario = random.choice(usuarios)
            libro = random.choice(libros)
            if (usuario, libro) not in used_pairs:
                CarritoItem.objects.create(
                    usuario=usuario,
                    libro=libro,
                    cantidad=random.randint(1, 3)
                )
                used_pairs.add((usuario, libro))
        self.stdout.write(self.style.SUCCESS("Carrito items created."))

        # --- 5. Create Resenas ---
        self.stdout.write("Creating 10 Reseñas...")
        used_pairs = set()
        for i in range(10):
            usuario = random.choice(usuarios)
            libro = random.choice(libros)
            if (usuario, libro) not in used_pairs:
                Resena.objects.create(
                    libro=libro,
                    usuario=usuario,
                    calificacion=random.randint(3, 5),
                    comentario=f'Este es un comentario de reseña número {i}. ¡Gran libro!',
                    aprobada=True
                )
                used_pairs.add((usuario, libro))
        self.stdout.write(self.style.SUCCESS("Reseñas created."))

        # --- 6. Create Cupones ---
        self.stdout.write("Creating 10 Cupones...")
        for i in range(10):
            tipo = random.choice(['porcentaje', 'fijo'])
            valor = random.randint(10, 25) if tipo == 'porcentaje' else random.randint(5, 10)
            Cupon.objects.create(
                codigo=f'DESCUENTO{i}{random.randint(100,999)}',
                descripcion=f'Cupón de prueba número {i}',
                tipo_descuento=tipo,
                valor=Decimal(valor),
                uso_maximo=100,
                fecha_inicio=timezone.now() - timedelta(days=1),
                fecha_fin=timezone.now() + timedelta(days=30),
                activo=True
            )
        self.stdout.write(self.style.SUCCESS("Cupones created."))

        # --- 7. Create Pedidos, Detalles, Entregas y Historial ---
        self.stdout.write("Creating 10 Pedidos with all related items...")
        for i in range(10):
            usuario_pedido = random.choice(usuarios)
            
            # Create Pedido
            pedido = Pedido.objects.create(
                usuario=usuario_pedido,
                estado=random.choice(['pagado', 'completado']),
                metodo_pago=random.choice(['simulado', 'paypal']),
            )
            HistorialPedido.objects.create(
                pedido=pedido,
                usuario=usuario_pedido,
                accion="Pedido Creado",
                descripcion="El pedido fue creado por el cliente."
            )
            
            # Create Detalles de Pedido (1 a 3 libros por pedido)
            libros_en_pedido = random.sample(libros, random.randint(1, 3))
            for libro_pedido in libros_en_pedido:
                cantidad = random.randint(1, 2)
                precio = libro_pedido.precio_actual()
                DetallePedido.objects.create(
                    pedido=pedido,
                    libro=libro_pedido,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    precio_total=precio * cantidad
                )
                
                # Create Entrega Digital for each item
                if pedido.estado in ['pagado', 'completado']:
                    EntregaDigital.objects.create(
                        pedido=pedido,
                        libro=libro_pedido,
                        usuario=usuario_pedido,
                        expiracion=timezone.now() + timedelta(days=365)
                    )

            # Update Pedido totals and status
            pedido.calcular_totales()
            if pedido.estado in ['pagado', 'completado']:
                pedido.marcar_como_pagado()
                HistorialPedido.objects.create(
                    pedido=pedido,
                    usuario=None,
                    accion="Pago Confirmado",
                    descripcion=f"El pago fue confirmado a través de {pedido.metodo_pago}."
                )

        self.stdout.write(self.style.SUCCESS("Pedidos, Detalles, Entregas and Historial created."))
        self.stdout.write(self.style.SUCCESS("Database population complete!"))
