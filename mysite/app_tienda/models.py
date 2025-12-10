from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
import random
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils.text import slugify

# 1. USUARIO PERSONALIZADO
class Usuario(AbstractUser):
    TIPO_USUARIO = [
        ('cliente', 'Cliente'),
        ('administrador', 'Administrador'),
        ('staff', 'Staff'),
    ]
    
    email = models.EmailField(unique=True, verbose_name="Correo electrónico")
    telefono = models.CharField(max_length=15, blank=True, null=True)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO, default='cliente')
    fecha_registro = models.DateTimeField(default=timezone.now)
    email_verificado = models.BooleanField(default=False)
    token_verificacion = models.UUIDField(default=uuid.uuid4, editable=False)
    direccion_envio = models.TextField(blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        permissions = [
            ("acceso_panel_admin", "Puede acceder al panel de administración"),
            ("gestionar_libros", "Puede gestionar libros"),
            ("gestionar_pedidos", "Puede gestionar pedidos"),
            ("gestionar_usuarios", "Puede gestionar usuarios"),
            ("ver_reportes", "Puede ver reportes"),
        ]
    
    def __str__(self):
        return self.email
    
    def es_administrador(self):
        return self.tipo_usuario == 'administrador' or self.is_staff
    
    def obtener_carrito(self):
        return CarritoItem.objects.filter(usuario=self)

# 2. CATEGORÍA
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    imagen = models.ImageField(upload_to='categorias/', blank=True, null=True)
    activa = models.BooleanField(default=True)
    orden = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['orden', 'nombre']
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super(Categoria, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.nombre

# 3. LIBRO (PRODUCTO DIGITAL)
class Libro(models.Model):
    FORMATO_CHOICES = [
        ('pdf', 'PDF'),
        ('epub', 'EPUB'),
        ('mobi', 'MOBI'),
    ]
    
    # Información básica
    titulo = models.CharField(max_length=200, verbose_name="Título")
    autor = models.CharField(max_length=150, verbose_name="Autor")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='libros')
    descripcion = models.TextField(verbose_name="Descripción")
    descripcion_corta = models.CharField(max_length=300, blank=True, null=True)
    
    # Precios
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    precio_descuento = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    en_oferta = models.BooleanField(default=False)
    
    # Información digital
    formato = models.CharField(max_length=10, choices=FORMATO_CHOICES, default='pdf')
    archivo_digital = models.FileField(upload_to='libros_digitales/', verbose_name="Archivo digital")
    tamanio_archivo = models.CharField(max_length=20, blank=True, editable=False)
    paginas = models.IntegerField(blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True, unique=True)
    
    # Multimedia
    portada = models.ImageField(upload_to='portadas/', verbose_name="Portada")
    vista_previa = models.FileField(upload_to='vistas_previas/', blank=True, null=True, verbose_name="Vista previa")
    
    # Metadatos
    destacado = models.BooleanField(default=False, verbose_name="Destacar en página principal")
    nuevo = models.BooleanField(default=True, verbose_name="Marcar como nuevo")
    activo = models.BooleanField(default=True, verbose_name="Disponible para venta")
    stock_ilimitado = models.BooleanField(default=True, verbose_name="Stock ilimitado (digital)")
    
    # SEO
    slug = models.SlugField(unique=True, blank=True)
    meta_descripcion = models.CharField(max_length=160, blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='libros_creados')
    
    class Meta:
        verbose_name = "Libro"
        verbose_name_plural = "Libros"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=['titulo']),
            models.Index(fields=['autor']),
            models.Index(fields=['categoria']),
            models.Index(fields=['precio']),
            models.Index(fields=['destacado']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.autor}"
    
    def precio_actual(self):
        return self.precio_descuento if self.en_oferta and self.precio_descuento else self.precio
    
    def porcentaje_descuento(self):
        if self.en_oferta and self.precio_descuento and self.precio > 0:
            return int(((self.precio - self.precio_descuento) / self.precio) * 100)
        return 0
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        
        if self.precio_descuento and self.precio_descuento > 0 and self.precio_descuento < self.precio:
            self.en_oferta = True
        else:
            self.en_oferta = False
            self.precio_descuento = None

        if self.archivo_digital:
            self.tamanio_archivo = self._get_file_size(self.archivo_digital.size)
        
        super().save(*args, **kwargs)
    
    def _get_file_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

# 4. CARRITO
class CarritoItem(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='carrito')
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    fecha_agregado = models.DateTimeField(auto_now_add=True)
    fecha_actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Item del carrito"
        verbose_name_plural = "Items del carrito"
        unique_together = ['usuario', 'libro']
    
    def __str__(self):
        return f"{self.libro.titulo} x {self.cantidad}"
    
    def subtotal(self):
        return self.libro.precio_actual() * self.cantidad

# 5. PEDIDO
class Pedido(models.Model):
    ESTADO_PEDIDO = [
        ('pendiente_pago', 'Pendiente de pago'),
        ('pagado', 'Pagado'),
        ('procesando', 'Procesando'),
        ('completado', 'Completado'),
        ('reembolsado', 'Reembolsado'),
        ('cancelado', 'Cancelado'),
    ]
    
    METODO_PAGO = [
        ('simulado', 'Simulado'),
        ('paypal', 'PayPal'),
        ('transferencia', 'Transferencia'),
    ]
    
    # Relaciones
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='pedidos')
    
    # Información del pedido
    numero_pedido = models.CharField(max_length=32, unique=True, editable=False)
    estado = models.CharField(max_length=20, choices=ESTADO_PEDIDO, default='pendiente_pago')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO, blank=True, null=True, default='simulado')
    
    # Totales
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Pagos
    pagado = models.BooleanField(default=False)
    fecha_pago = models.DateTimeField(blank=True, null=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=['numero_pedido']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_creacion']),
        ]
    
    def __str__(self):
        return f"Pedido #{self.numero_pedido}"
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            self.numero_pedido = self._generar_numero_pedido()
        super().save(*args, **kwargs)
    
    def _generar_numero_pedido(self):
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        random_part = random.randint(1000, 9999)
        return f"ORD-{timestamp}-{self.usuario.id:04d}-{random_part}"
    
    def calcular_totales(self):
        detalles = self.detalles.all()
        self.subtotal = sum(detalle.subtotal() for detalle in detalles)
        self.impuestos = self.subtotal * Decimal('0.16')  # 16% IVA
        self.total = self.subtotal + self.impuestos
        self.save()
    
    def marcar_como_pagado(self):
        self.estado = 'pagado'
        self.pagado = True
        self.fecha_pago = timezone.now()
        self.save()

# 6. DETALLE PEDIDO
class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = "Detalle del pedido"
        verbose_name_plural = "Detalles del pedido"
    
    def __str__(self):
        return f"{self.libro.titulo} x {self.cantidad}"
    
    def subtotal(self):
        return self.precio_unitario * self.cantidad

# 7. ENTREGA DIGITAL
class EntregaDigital(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='entregas')
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='entregas_digitales')
    
    # Token seguro
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    token_acceso = models.CharField(max_length=64, blank=True, editable=False)
    
    # Control de acceso
    expiracion = models.DateTimeField()
    descargas_permitidas = models.IntegerField(default=3)
    descargas_realizadas = models.IntegerField(default=0)
    
    # Seguimiento
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    primera_descarga = models.DateTimeField(blank=True, null=True)
    ultima_descarga = models.DateTimeField(blank=True, null=True)
    ip_ultima_descarga = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Entrega digital"
        verbose_name_plural = "Entregas digitales"
        unique_together = ['pedido', 'libro']
    
    def __str__(self):
        return f"Entrega de {self.libro.titulo}"
    
    def es_valido(self):
        return timezone.now() < self.expiracion and self.descargas_realizadas < self.descargas_permitidas

    def registrar_descarga(self, ip_address):
        if self.descargas_realizadas == 0:
            self.primera_descarga = timezone.now()
        self.descargas_realizadas += 1
        self.ultima_descarga = timezone.now()
        self.ip_ultima_descarga = ip_address
        self.save()
    
    def dias_restantes(self):
        from datetime import datetime
        if self.expiracion:
            delta = self.expiracion - timezone.now()
            return max(0, delta.days)
        return 0

# 8. RESEÑAS
class Resena(models.Model):
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, related_name='resenas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    calificacion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField()
    aprobada = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Reseña"
        verbose_name_plural = "Reseñas"
        unique_together = ['libro', 'usuario']
    
    def __str__(self):
        return f"Reseña de {self.usuario} para {self.libro}"

# 9. WISHLIST
class Wishlist(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='wishlist')
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    fecha_agregado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Wishlist"
        verbose_name_plural = "Wishlists"
        unique_together = ['usuario', 'libro']
    
    def __str__(self):
        return f"{self.usuario} - {self.libro}"

# 10. CUPONES/DESCUENTOS
class Cupon(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    tipo_descuento = models.CharField(max_length=10, choices=[('porcentaje', 'Porcentaje'), ('fijo', 'Fijo')])
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    uso_maximo = models.IntegerField(default=1)
    usos_realizados = models.IntegerField(default=0)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"
    
    def __str__(self):
        return self.codigo
    
    def es_valido(self):
        ahora = timezone.now()
        return (
            self.activo and
            self.usos_realizados < self.uso_maximo and
            self.fecha_inicio <= ahora <= self.fecha_fin
        )

# 11. HISTORIAL DE PEDIDOS (para auditoría)
class HistorialPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historial')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='historial_usuario')
    accion = models.CharField(max_length=50) # Ej: 'creado', 'actualizado_estado', 'pagado', 'cancelado'
    descripcion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Historial de Pedido"
        verbose_name_plural = "Historial de Pedidos"
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"[{self.fecha_registro.strftime('%Y-%m-%d %H:%M')}] Pedido {self.pedido.numero_pedido} - {self.accion}"