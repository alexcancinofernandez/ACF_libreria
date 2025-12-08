from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse, HttpResponseForbidden, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
import stripe
import json
import uuid
from datetime import timedelta, datetime
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

    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    if precio_min:
        libros = libros.filter(precio__gte=precio_min)
    if precio_max:
        libros = libros.filter(precio__lte=precio_max)
    
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
    libros_relacionados = Libro.objects.filter(
        categoria=libro.categoria
    ).exclude(id=libro.id)[:4]
    
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

def ofertas(request):
    libros_en_oferta = Libro.objects.filter(en_oferta=True, activo=True)
    paginator = Paginator(libros_en_oferta, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'titulo_pagina': 'Libros en Oferta'
    }
    return render(request, 'app_tienda/ofertas.html', context)

def contacto(request):
    return render(request, 'app_tienda/contacto.html')

# ========== VISTAS DE USUARIO AUTENTICADO ==========

@login_required
def perfil(request):
    usuario = request.user
    pedidos = Pedido.objects.filter(usuario=usuario).order_by('-fecha_creacion')[:10]
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('perfil')
    else:
        form = PerfilForm(instance=usuario)
    
    context = {
        'usuario': usuario,
        'pedidos': pedidos,
        'form': form,
    }
    return render(request, 'app_tienda/perfil.html', context)

@login_required
def carrito(request):
    items = CarritoItem.objects.filter(usuario=request.user)
    subtotal = sum(item.subtotal() for item in items)
    impuestos = subtotal * 0.16
    total = subtotal + impuestos
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'impuestos': impuestos,
        'total': total,
    }
    return render(request, 'app_tienda/carrito.html', context)

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
    return redirect('carrito')

@login_required
def actualizar_carrito(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        action = data.get('action')
        
        try:
            item = CarritoItem.objects.get(id=item_id, usuario=request.user)
            
            if action == 'increment':
                item.cantidad += 1
            elif action == 'decrement':
                if item.cantidad > 1:
                    item.cantidad -= 1
                else:
                    item.delete()
                    return JsonResponse({'success': True, 'removed': True})
            elif action == 'remove':
                item.delete()
                return JsonResponse({'success': True, 'removed': True})
            
            item.save()
            
            items = CarritoItem.objects.filter(usuario=request.user)
            subtotal = sum(i.subtotal() for i in items)
            impuestos = subtotal * 0.16
            total = subtotal + impuestos
            
            return JsonResponse({
                'success': True,
                'cantidad': item.cantidad,
                'subtotal_item': float(item.subtotal()),
                'subtotal': float(subtotal),
                'impuestos': float(impuestos),
                'total': float(total),
            })
        except CarritoItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item no encontrado'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def checkout(request):
    items = CarritoItem.objects.filter(usuario=request.user)
    if not items.exists():
        return redirect('carrito')
    
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
        
        return redirect('proceso_pago')
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'impuestos': impuestos,
        'total': total,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, 'app_tienda/checkout.html', context)

@login_required
def proceso_pago(request):
    pedido_id = request.session.get('pedido_id')
    if not pedido_id:
        return redirect('carrito')
    
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    line_items = []
    for detalle in pedido.detalles.all():
        line_items.append({
            'price_data': {
                'currency': settings.STRIPE_CURRENCY,
                'product_data': {
                    'name': detalle.libro.titulo,
                    'description': f'Autor: {detalle.libro.autor}',
                },
                'unit_amount': int(detalle.precio_unitario * 100),
            },
            'quantity': detalle.cantidad,
        })
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(f'/pago-exitoso/{pedido.numero_pedido}/'),
            cancel_url=request.build_absolute_uri('/carrito/'),
            customer_email=request.user.email,
            metadata={'pedido_id': str(pedido.id)},
        )
        
        pedido.stripe_session_id = checkout_session.id
        pedido.save()
        
        return redirect(checkout_session.url)
    
    except Exception as e:
        return render(request, 'app_tienda/error_pago.html', {'error': str(e)})

@login_required
def pago_exitoso(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido, usuario=request.user)
    
    if pedido.estado == 'pendiente_pago':
        pedido.marcar_como_pagado()
        pedido.estado = 'completado'
        pedido.save()
        
        generar_entregas_digitales(pedido)
        
        enviar_email_confirmacion(pedido)
        
        CarritoItem.objects.filter(usuario=request.user).delete()
        
        request.session.pop('pedido_id', None)
    
    context = {'pedido': pedido}
    return render(request, 'app_tienda/pago_exitoso.html', context)

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
    entregas = EntregaDigital.objects.filter(
        pedido__usuario=request.user,
        pedido__estado__in=['pagado', 'completado']
    ).select_related('libro', 'pedido')
    
    context = {'entregas': entregas}
    return render(request, 'app_tienda/mis_descargas.html', context)

@login_required
def descargar_libro(request, token):
    entrega = get_object_or_404(EntregaDigital, token=token)
    
    if entrega.pedido.usuario != request.user:
        return HttpResponseForbidden("No tienes permiso para descargar este archivo")
    
    if not entrega.esta_disponible():
        return HttpResponseForbidden("Este enlace ha expirado o ha alcanzado el límite de descargas")
    
    entrega.registrar_descarga(request.META.get('REMOTE_ADDR'))
    
    libro = entrega.libro
    response = FileResponse(libro.archivo_digital.open(), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{libro.titulo}.{libro.formato}"'
    
    return response

@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(usuario=request.user).select_related('libro')
    
    context = {'wishlist_items': wishlist_items}
    return render(request, 'app_tienda/wishlist.html', context)

@login_required
def agregar_wishlist(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    Wishlist.objects.get_or_create(usuario=request.user, libro=libro)
    return redirect('wishlist')

@login_required
def eliminar_wishlist(request, libro_id):
    Wishlist.objects.filter(usuario=request.user, libro_id=libro_id).delete()
    return redirect('wishlist')

# ========== WEBHOOK STRIPE ==========

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        try:
            pedido = Pedido.objects.get(stripe_session_id=session.id)
            pedido.marcar_como_pagado()
            pedido.stripe_payment_intent_id = session.payment_intent
            pedido.save()
            
            generar_entregas_digitales(pedido)
            
            enviar_email_confirmacion(pedido)
            
        except Pedido.DoesNotExist:
            pass
    
    return JsonResponse({'status': 'success'})

# ========== FUNCIONES AUXILIARES ==========

def generar_entregas_digitales(pedido):
    for detalle in pedido.detalles.all():
        expiracion = timezone.now() + timedelta(days=30)
        
        EntregaDigital.objects.create(
            pedido=pedido,
            libro=detalle.libro,
            expiracion=expiracion,
        )

def enviar_email_confirmacion(pedido):
    entregas = EntregaDigital.objects.filter(pedido=pedido)
    
    enlaces = []
    for entrega in entregas:
        url = reverse('descargar_libro', args=[str(entrega.token)])
        enlaces.append({
            'titulo': entrega.libro.titulo,
            'url': url,
            'expiracion': entrega.expiracion,
        })
    
    context = {
        'pedido': pedido,
        'enlaces': enlaces,
    }
    
    html_message = render_to_string('app_tienda/emails/pedido_confirmado.html', context)
    plain_message = f'''
    Gracias por tu compra en Librería Cancino.
    
    Tu pedido #{pedido.numero_pedido} ha sido confirmado.
    Total: ${pedido.total}
    
    Puedes descargar tus libros desde tu cuenta:
    https://tusitio.com/mis-descargas/
    
    Los enlaces expiran en 30 días.
    '''
    
    send_mail(
        subject=f'Confirmación de pedido #{pedido.numero_pedido}',
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[pedido.usuario.email],
        html_message=html_message,
        fail_silently=False,
    )

# ========== VISTAS DE ADMINISTRACIÓN ==========

def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.tipo_usuario == 'administrador')

@user_passes_test(es_administrador)
def admin_dashboard(request):
    total_ingresos = Pedido.objects.filter(estado__in=['pagado', 'completado']).aggregate(Sum('total'))['total__sum'] or 0
    total_pedidos = Pedido.objects.count()
    total_usuarios = Usuario.objects.count()
    pedidos_recientes = Pedido.objects.order_by('-fecha_creacion')[:5]
    
    context = {
        'total_ingresos': total_ingresos,
        'total_pedidos': total_pedidos,
        'total_usuarios': total_usuarios,
        'pedidos_recientes': pedidos_recientes,
    }
    return render(request, 'app_tienda/admin/admin_dashboard.html', context)

@user_passes_test(es_administrador)
def admin_pedidos(request):
    pedidos_list = Pedido.objects.all().order_by('-fecha_creacion')
    
    query = request.GET.get('q')
    if query:
        pedidos_list = pedidos_list.filter(
            Q(numero_pedido__icontains=query) |
            Q(usuario__first_name__icontains=query) |
            Q(usuario__last_name__icontains=query) |
            Q(usuario__email__icontains=query)
        )

    estado = request.GET.get('estado')
    if estado:
        pedidos_list = pedidos_list.filter(estado=estado)
        
    paginator = Paginator(pedidos_list, 20)
    page_number = request.GET.get('page')
    pedidos = paginator.get_page(page_number)
    
    context = {
        'pedidos': pedidos,
        'estados': Pedido.ESTADO_CHOICES,
    }
    return render(request, 'app_tienda/admin/admin_pedidos.html', context)


@user_passes_test(es_administrador)
def admin_detalle_pedido(request, numero_pedido):
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Pedido.ESTADO_CHOICES):
            pedido.estado = nuevo_estado
            pedido.save()
            # Lógica para notificar al usuario, etc.
            return redirect('app_tienda:admin_detalle_pedido', numero_pedido=pedido.numero_pedido)
            
    context = {
        'pedido': pedido,
        'estados_pedido': Pedido.ESTADO_CHOICES,
    }
    return render(request, 'app_tienda/admin/admin_detalle_pedido.html', context)


@user_passes_test(es_administrador)
def admin_libros(request):
    libros_list = Libro.objects.all().order_by('-fecha_creacion')
    query = request.GET.get('q')
    if query:
        libros_list = libros_list.filter(
            Q(titulo__icontains=query) | 
            Q(autor__icontains=query) | 
            Q(isbn__icontains=query)
        )
    
    paginator = Paginator(libros_list, 15)
    page_number = request.GET.get('page')
    libros = paginator.get_page(page_number)
    
    context = {
        'libros': libros,
    }
    return render(request, 'app_tienda/admin/admin_libros.html', context)

@user_passes_test(es_administrador)
def admin_crear_libro(request):
    if request.method == 'POST':
        form = LibroForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('app_tienda:admin_libros')
    else:
        form = LibroForm()
    
    context = {
        'form': form,
    }
    return render(request, 'app_tienda/admin/admin_libro_form.html', context)

@user_passes_test(es_administrador)
def admin_editar_libro(request, slug):
    libro = get_object_or_404(Libro, slug=slug)
    if request.method == 'POST':
        form = LibroForm(request.POST, request.FILES, instance=libro)
        if form.is_valid():
            form.save()
            return redirect('app_tienda:admin_libros')
    else:
        form = LibroForm(instance=libro)
    
    context = {
        'form': form,
        'libro': libro,
    }
    return render(request, 'app_tienda/admin/admin_libro_form.html', context)

@user_passes_test(es_administrador)
def admin_eliminar_libro(request, slug):
    libro = get_object_or_404(Libro, slug=slug)
    if request.method == 'POST':
        libro.delete()
        return redirect('app_tienda:admin_libros')
    # No se necesita un template para GET, se maneja con un modal en el listado
    return redirect('app_tienda:admin_libros')

@user_passes_test(es_administrador)
def admin_usuarios(request):
    usuarios_list = Usuario.objects.all().order_by('-date_joined')
    
    query = request.GET.get('q')
    if query:
        usuarios_list = usuarios_list.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(username__icontains=query)
        )

    tipo = request.GET.get('tipo')
    if tipo == 'cliente':
        usuarios_list = usuarios_list.filter(is_staff=False, tipo_usuario='cliente')
    elif tipo == 'administrador':
        usuarios_list = usuarios_list.filter(Q(is_staff=True) | Q(tipo_usuario='administrador'))

    paginator = Paginator(usuarios_list, 20)
    page_number = request.GET.get('page')
    usuarios = paginator.get_page(page_number)
    
    context = {
        'usuarios': usuarios,
    }
    return render(request, 'app_tienda/admin/admin_usuarios.html', context)

@user_passes_test(es_administrador)
def admin_reportes(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    base_query = Pedido.objects.filter(estado__in=['pagado', 'completado'])

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        base_query = base_query.filter(fecha_creacion__gte=start_date)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        base_query = base_query.filter(fecha_creacion__lte=end_date)

    sales_data = (
        base_query
        .extra(select={'fecha': 'date(fecha_creacion)'})
        .values('fecha')
        .annotate(total=Sum('total'))
        .order_by('fecha')
    )

    sales_data_json = json.dumps([{
        'fecha': item['fecha'].strftime('%Y-%m-%d'), 
        'total': float(item['total'])
    } for item in sales_data])

    libros_mas_vendidos = DetallePedido.objects.filter(
        pedido__in=base_query
    ).values('libro__titulo').annotate(
        unidades_vendidas=Sum('cantidad')
    ).order_by('-unidades_vendidas')[:10]
    
    top_clientes = Pedido.objects.filter(
        pk__in=base_query.values_list('pk', flat=True)
    ).values(
        'usuario__first_name', 'usuario__last_name'
    ).annotate(
        total_gastado=Sum('total')
    ).order_by('-total_gastado')[:10]

    context = {
        'sales_data_json': sales_data_json,
        'libros_mas_vendidos': libros_mas_vendidos,
        'top_clientes': top_clientes,
    }
    return render(request, 'app_tienda/admin/admin_reportes.html', context)