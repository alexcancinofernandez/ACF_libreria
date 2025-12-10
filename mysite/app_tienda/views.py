
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse, HttpResponseForbidden, FileResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
import json
import uuid
from datetime import timedelta
from django.urls import reverse
from decimal import Decimal
from django.db import transaction

from .models import *
from .forms import *

# ========== VISTAS PÚBLICAS ==========#

def index(request):
    libros_destacados = Libro.objects.filter(destacado=True, activo=True)[:8]
    libros_nuevos = Libro.objects.filter(nuevo=True, activo=True)[:8]
    libros_oferta = Libro.objects.filter(en_oferta=True, activo=True)[:8]
    
    categorias = Categoria.objects.filter(activa=True)
    
    context = {
        'libros_destacados': libros_destacados,
        'libros_nuevos': libros_nuevos,
        'libros_oferta': libros_oferta,
        'categorias': categorias,
    }
    return render(request, 'app_tienda/public/index.html', context)

def catalogo(request):
    libros = Libro.objects.filter(activo=True)
    
    # Crear una copia mutable de request.GET para poder modificarla
    filtros_mutables = request.GET.copy()

    categoria_id = filtros_mutables.get('categoria')
    if categoria_id:
        libros = libros.filter(categoria_id=categoria_id)
    
    q = filtros_mutables.get('q')
    if q:
        libros = libros.filter(Q(titulo__icontains=q) | Q(autor__icontains=q) | Q(categoria__nombre__icontains=q))

    precio_min_str = filtros_mutables.get('precio_min')
    if precio_min_str:
        try:
            precio_min = float(precio_min_str)
            libros = libros.filter(precio__gte=precio_min)
        except (ValueError, TypeError):
            pass

    precio_max_str = filtros_mutables.get('precio_max')
    if precio_max_str:
        try:
            precio_max = float(precio_max_str)
            libros = libros.filter(precio__lte=precio_max)
        except (ValueError, TypeError):
            pass
    
    orden = filtros_mutables.get('orden', 'recientes')
    if orden == 'precio_asc':
        libros = libros.order_by('precio')
    elif orden == 'precio_desc':
        libros = libros.order_by('-precio')
    elif orden == 'titulo':
        libros = libros.order_by('titulo')
    else:
        libros = libros.order_by('-fecha_creacion')
    
    # Eliminar el parámetro 'page' de la URL para que no se acumule
    if 'page' in filtros_mutables:
        del filtros_mutables['page']

    paginator = Paginator(libros, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categorias = Categoria.objects.filter(activa=True)
    
    context = {
        'page_obj': page_obj,
        'categorias': categorias,
        'filtros': filtros_mutables.urlencode(),
    }
    return render(request, 'app_tienda/public/catalogo.html', context)

def detalle_libro(request, slug):
    libro = get_object_or_404(Libro, slug=slug, activo=True)
    libros_relacionados = Libro.objects.filter(categoria=libro.categoria).exclude(id=libro.id)[:4]
    
    ya_comprado = False
    if request.user.is_authenticated:
        ya_comprado = Pedido.objects.filter(
            usuario=request.user,
            detalles__libro=libro,
            estado__in=['pagado', 'completado']
        ).exists()
    
    context = {
        'libro': libro,
        'libros_relacionados': libros_relacionados,
        'ya_comprado': ya_comprado,
    }
    return render(request, 'app_tienda/public/detalle_libro.html', context)

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('app_tienda:index')
    else:
        form = RegistroForm()
    return render(request, 'app_tienda/registration/registro.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        # Los datos pueden ser email o username
        identifier = request.POST.get('email') 
        password = request.POST.get('password')
        
        # Intentamos autenticar usando el email como username
        user = authenticate(request, username=identifier, password=password)
        
        # Si falla, intentamos encontrar el usuario por email y luego autenticar con su username real
        if user is None:
            try:
                # El campo de entrada 'email' se usa para el identificador
                q = Q(email__iexact=identifier) | Q(username__iexact=identifier)
                user_obj = Usuario.objects.get(q)
                user = authenticate(request, username=user_obj.username, password=password)
            except Usuario.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next')
            return redirect(next_url or 'app_tienda:index')
        else:
            # Usar un mensaje de error genérico por seguridad
            error_message = "El correo electrónico o la contraseña son incorrectos. Por favor, inténtalo de nuevo."
            return render(request, 'app_tienda/registration/login.html', {'error': error_message})
            
    return render(request, 'app_tienda/registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('app_tienda:index')

def ofertas(request):
    libros_oferta = Libro.objects.filter(
        en_oferta=True, 
        activo=True,
        precio_descuento__isnull=False,
        precio_descuento__gt=0
    )
    context = {
        'libros_oferta': libros_oferta
    }
    return render(request, 'app_tienda/public/ofertas.html', context)

def contacto(request):
    if request.method == 'POST':
        return redirect('app_tienda:index')
    return render(request, 'app_tienda/public/contacto.html')


# ========== VISTAS DE USUARIO AUTENTICADO ==========#

@login_required
def perfil(request):
    usuario = request.user
    pedidos = Pedido.objects.filter(usuario=usuario).order_by('-fecha_creacion')[:10]
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('app_tienda:perfil')
    else:
        form = PerfilForm(instance=usuario)
    
    context = {
        'usuario': usuario,
        'pedidos': pedidos,
        'form': form,
    }
    return render(request, 'app_tienda/user/perfil.html', context)


@login_required
def carrito(request):
    items = CarritoItem.objects.filter(usuario=request.user)
    subtotal = sum(item.subtotal() for item in items)
    context = {'items': items, 'subtotal': subtotal}
    return render(request, 'app_tienda/user/carrito.html', context)

@login_required
def agregar_al_carrito(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id, activo=True)
    item, created = CarritoItem.objects.get_or_create(
        usuario=request.user,
        libro=libro,
        defaults={'cantidad': 1}
    )
    if not created:
        item.cantidad += 1
        item.save()
    return redirect('app_tienda:carrito')

@login_required
def actualizar_carrito(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        cantidad = int(request.POST.get('cantidad'))
        item = get_object_or_404(CarritoItem, id=item_id, usuario=request.user)
        if cantidad > 0:
            item.cantidad = cantidad
            item.save()
        else:
            item.delete()
    return redirect('app_tienda:carrito')

@login_required
def checkout(request):
    items = CarritoItem.objects.filter(usuario=request.user)
    if not items.exists():
        return redirect('app_tienda:carrito')
    
    subtotal = sum(item.subtotal() for item in items)
    impuestos = subtotal * Decimal('0.16')
    total = subtotal + impuestos
    
    if request.method == 'POST':
        with transaction.atomic():
            pedido = Pedido.objects.create(
                usuario=request.user,
                subtotal=subtotal,
                impuestos=impuestos,
                total=total,
                metodo_pago='simulado'
            )
            
            for item in items:
                DetallePedido.objects.create(
                    pedido=pedido,
                    libro=item.libro,
                    cantidad=item.cantidad,
                    precio_unitario=item.libro.precio_actual(),
                    precio_total=item.subtotal(),
                )
            
            pedido.marcar_como_pagado()

            for detalle in pedido.detalles.all():
                EntregaDigital.objects.create(
                    pedido=pedido,
                    libro=detalle.libro,
                    usuario=request.user,
                    expiracion=timezone.now() + timedelta(days=365)
                )

            CarritoItem.objects.filter(usuario=request.user).delete()
        
        return redirect(reverse('app_tienda:pedido_confirmacion', kwargs={'numero_pedido': pedido.numero_pedido}))
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'impuestos': impuestos,
        'total': total,
    }
    return render(request, 'app_tienda/user/checkout.html', context)

@login_required
def pedido_confirmacion(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido, usuario=request.user)
    context = {'pedido': pedido}
    return render(request, 'app_tienda/user/pedido_confirmacion.html', context)


@login_required
def mis_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    context = {'pedidos': pedidos}
    return render(request, 'app_tienda/user/mis_pedidos.html', context)

@login_required
def detalle_pedido(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido, usuario=request.user)
    context = {'pedido': pedido}
    return render(request, 'app_tienda/user/detalle_pedido.html', context)

@login_required
def mis_descargas(request):
    descargas = EntregaDigital.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    context = {'descargas': descargas}
    return render(request, 'app_tienda/user/mis_descargas.html', context)

@login_required
def descargar_libro(request, token):
    entrega = get_object_or_404(EntregaDigital, token=token, usuario=request.user)
    if not entrega.es_valido():
        return HttpResponseForbidden("El enlace de descarga ha expirado o no es válido.")

    entrega.registrar_descarga(request.META.get('REMOTE_ADDR'))

    file_path = entrega.libro.archivo_digital.path
    file_name = f'{entrega.libro.slug}.{entrega.libro.formato}'

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(usuario=request.user)
    context = {'items': items}
    return render(request, 'app_tienda/user/wishlist.html', context)

@login_required
def agregar_wishlist(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    Wishlist.objects.get_or_create(usuario=request.user, libro=libro)
    return redirect('app_tienda:wishlist')

@login_required
def eliminar_wishlist(request, libro_id):
    Wishlist.objects.filter(usuario=request.user, libro_id=libro_id).delete()
    return redirect('app_tienda:wishlist')

@login_required
def mover_wishlist_a_carrito(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            wishlist_item = get_object_or_404(Wishlist, id=item_id, usuario=request.user)
            libro = wishlist_item.libro

            # Agregar al carrito
            carrito_item, created = CarritoItem.objects.get_or_create(
                usuario=request.user,
                libro=libro,
                defaults={'cantidad': 1}
            )
            if not created:
                carrito_item.cantidad += 1
                carrito_item.save()

            # Eliminar de la wishlist
            wishlist_item.delete()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# ========== VISTAS DE ADMINISTRACIÓN ==========#

def es_administrador(user):
    return user.is_authenticated and user.es_administrador()

@user_passes_test(es_administrador)
def admin_dashboard(request):
    return render(request, 'app_tienda/admin/dashboard.html')

@user_passes_test(es_administrador)
def admin_pedidos(request):
    pedidos = Pedido.objects.all().order_by('-fecha_creacion')
    context = {'pedidos': pedidos}
    return render(request, 'app_tienda/admin/pedidos.html', context)

@user_passes_test(es_administrador)
def admin_detalle_pedido(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)
    context = {'pedido': pedido}
    return render(request, 'app_tienda/admin/detalle_pedido.html', context)

@user_passes_test(es_administrador)
def admin_libros(request):
    libros = Libro.objects.all()
    context = {'libros': libros}
    return render(request, 'app_tienda/admin/libros.html', context)

@user_passes_test(es_administrador)
def admin_libro_form(request, slug=None):
    if slug:
        libro = get_object_or_404(Libro, slug=slug)
        form = LibroForm(instance=libro)
    else:
        libro = None
        form = LibroForm()
    
    if request.method == 'POST':
        form = LibroForm(request.POST, request.FILES, instance=libro)
        if form.is_valid():
            form.save()
            return redirect('app_tienda:admin_libros')

    context = {
        'form': form,
        'libro': libro
    }
    return render(request, 'app_tienda/admin/libro_form.html', context)

@user_passes_test(es_administrador)
def admin_eliminar_libro(request, slug):
    libro = get_object_or_404(Libro, slug=slug)
    if request.method == 'POST':
        libro.delete()
        return redirect('app_tienda:admin_libros')
    context = {'libro': libro}
    return render(request, 'app_tienda/admin/eliminar_libro.html', context)

@user_passes_test(es_administrador)
def admin_usuarios(request):
    usuarios = Usuario.objects.all()
    context = {'usuarios': usuarios}
    return render(request, 'app_tienda/admin/usuarios.html', context)
