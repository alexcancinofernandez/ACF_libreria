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

from .models import *
from .forms import *

# ========== VISTAS PÚBLICAS ==========

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
    return render(request, 'app_tienda/index.html', context)

def catalogo(request):
    libros = Libro.objects.filter(activo=True)
    
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        libros = libros.filter(categoria_id=categoria_id)
    
    q = request.GET.get('q')
    if q:
        libros = libros.filter(Q(titulo__icontains=q) | Q(autor__icontains=q) | Q(categoria__nombre__icontains=q))

    # Filtro de precio robusto
    precio_min_str = request.GET.get('precio_min')
    if precio_min_str:
        try:
            precio_min = float(precio_min_str)
            libros = libros.filter(precio__gte=precio_min)
        except (ValueError, TypeError):
            pass

    precio_max_str = request.GET.get('precio_max')
    if precio_max_str:
        try:
            precio_max = float(precio_max_str)
            libros = libros.filter(precio__lte=precio_max)
        except (ValueError, TypeError):
            pass
    
    orden = request.GET.get('orden', 'recientes')
    if orden == 'precio_asc':
        libros = libros.order_by('precio')
    elif orden == 'precio_desc':
        libros = libros.order_by('-precio')
    elif orden == 'titulo':
        libros = libros.order_by('titulo')
    else:
        libros = libros.order_by('-fecha_creacion')
    
    paginator = Paginator(libros, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categorias = Categoria.objects.filter(activa=True)
    
    context = {
        'page_obj': page_obj,
        'categorias': categorias,
        'filtros': request.GET,
    }
    return render(request, 'app_tienda/catalogo.html', context)

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
    return render(request, 'app_tienda/detalle_libro.html', context)

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('app_tienda:index')
    else:
        form = RegistroForm()
    return render(request, 'app_tienda/registro.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'app_tienda:index')
            return redirect(next_url)
        else:
            return render(request, 'app_tienda/login.html', {'error': 'Credenciales inválidas'})
    return render(request, 'app_tienda/login.html')

def logout_view(request):
    logout(request)
    return redirect('app_tienda:index')

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
def pago_exitoso(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido, usuario=request.user)
    
    if pedido.estado == 'pendiente_pago':
        pedido.marcar_como_pagado()
        pedido.estado = 'completado'
        pedido.save()
        
        # generar_entregas_digitales(pedido)
        # enviar_email_confirmacion(pedido)
        CarritoItem.objects.filter(usuario=request.user).delete()
        request.session.pop('pedido_id', None)
    
    context = {'pedido': pedido}
    return render(request, 'app_tienda/pago_exitoso.html', context)


@login_required
def checkout(request):
    items = CarritoItem.objects.filter(usuario=request.user)
    if not items.exists():
        return redirect('app_tienda:carrito')
    
    subtotal = sum(item.subtotal() for item in items)
    impuestos = subtotal * 0.16
    total = subtotal + impuestos
    
    if request.method == 'POST':
        pedido = Pedido.objects.create(
            usuario=request.user,
            subtotal=subtotal,
            impuestos=impuestos,
            total=total,
        )
        
        for item in items:
            DetallePedido.objects.create(
                pedido=pedido,
                libro=item.libro,
                cantidad=item.cantidad,
                precio_unitario=item.libro.precio_actual(),
                precio_total=item.subtotal(),
            )
        
        request.session['pedido_id'] = pedido.id
        
        return redirect('app_tienda:proceso_pago')
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'impuestos': impuestos,
        'total': total,
    }
    return render(request, 'app_tienda/checkout.html', context)

@login_required
def proceso_pago(request):
    pedido_id = request.session.get('pedido_id')
    if not pedido_id:
        return redirect('app_tienda:checkout')

    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    # Simulate a successful payment
    return redirect(reverse('app_tienda:pago_exitoso', kwargs={'numero_pedido': pedido.numero_pedido}))

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
    return render(request, 'app_tienda/perfil.html', context)

@login_required
def agregar_wishlist(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    Wishlist.objects.get_or_create(usuario=request.user, libro=libro)
    return redirect('app_tienda:wishlist')

@login_required
def eliminar_wishlist(request, libro_id):
    Wishlist.objects.filter(usuario=request.user, libro_id=libro_id).delete()
    return redirect('app_tienda:wishlist')

def contacto(request):
    if request.method == 'POST':
        return redirect('app_tienda:index')
    return render(request, 'app_tienda/contacto.html')

@login_required
def carrito(request):
    items = CarritoItem.objects.filter(usuario=request.user)
    subtotal = sum(item.subtotal() for item in items)
    context = {'items': items, 'subtotal': subtotal}
    return render(request, 'app_tienda/carrito.html', context)

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
def mis_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    context = {'pedidos': pedidos}
    return render(request, 'app_tienda/mis_pedidos.html', context)

@login_required
def detalle_pedido(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido, usuario=request.user)
    context = {'pedido': pedido}
    return render(request, 'app_tienda/detalle_pedido.html', context)

@login_required
def mis_descargas(request):
    descargas = EntregaDigital.objects.filter(usuario=request.user, pedido__estado__in=['pagado', 'completado']).order_by('-pedido__fecha_creacion')
    context = {'descargas': descargas}
    return render(request, 'app_tienda/mis_descargas.html', context)

@login_required
def descargar_libro(request, token):
    entrega = get_object_or_404(EntregaDigital, token=token, usuario=request.user)
    if not entrega.es_valido():
        return HttpResponseForbidden("El enlace de descarga ha expirado o no es válido.")

    return FileResponse(open(entrega.libro.archivo_pdf.path, 'rb'), as_attachment=True, filename=f'{entrega.libro.slug}.pdf')

@login_required
def wishlist(request):
    items = Wishlist.objects.filter(usuario=request.user)
    context = {'items': items}
    return render(request, 'app_tienda/wishlist.html', context)

def is_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin)
def admin_dashboard(request):
    return render(request, 'app_tienda/admin/dashboard.html')

@user_passes_test(is_admin)
def admin_pedidos(request):
    return render(request, 'app_tienda/admin/pedidos.html')

@user_passes_test(is_admin)
def admin_detalle_pedido(request, numero_pedido):
    return render(request, 'app_tienda/admin/detalle_pedido.html')

@user_passes_test(is_admin)
def admin_libros(request):
    return render(request, 'app_tienda/admin/libros.html')

@user_passes_test(is_admin)
def admin_crear_libro(request):
    return render(request, 'app_tienda/admin/crear_libro.html')

@user_passes_test(is_admin)
def admin_editar_libro(request, slug):
    return render(request, 'app_tienda/admin/editar_libro.html')

@user_passes_test(is_admin)
def admin_eliminar_libro(request, slug):
    return render(request, 'app_tienda/admin/eliminar_libro.html')

@user_passes_test(is_admin)
def admin_usuarios(request):
    return render(request, 'app_tienda/admin/usuarios.html')

@user_passes_test(is_admin)
def admin_reportes(request):
    return render(request, 'app_tienda/admin/reportes.html')
