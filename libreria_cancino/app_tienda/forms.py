from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import *

class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'})
    )
    telefono = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono (opcional)'})
    )
    
    class Meta:
        model = Usuario
        fields = ['email', 'username', 'telefono']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError("Este correo ya está registrado")
        return email

class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'telefono']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

class LibroForm(forms.ModelForm):
    class Meta:
        model = Libro
        fields = '__all__'
        exclude = ['creado_por', 'fecha_creacion', 'fecha_actualizacion', 'tamanio_archivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'autor': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'descripcion_corta': forms.TextInput(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_descuento': forms.NumberInput(attrs={'class': 'form-control'}),
            'formato': forms.Select(attrs={'class': 'form-control'}),
            'paginas': forms.NumberInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_keywords': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_precio_descuento(self):
        precio = self.cleaned_data.get('precio')
        precio_descuento = self.cleaned_data.get('precio_descuento')
        
        if precio_descuento and precio_descuento >= precio:
            raise ValidationError("El precio de descuento debe ser menor al precio regular")
        return precio_descuento

class UsuarioAdminForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['email', 'username', 'first_name', 'last_name', 'telefono', 
                 'tipo_usuario', 'is_active', 'is_staff', 'is_superuser']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_usuario': forms.Select(attrs={'class': 'form-control'}),
        }

class CuponForm(forms.ModelForm):
    class Meta:
        model = Cupon
        fields = '__all__'
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo_descuento': forms.Select(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
            'uso_maximo': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

class BusquedaForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar libros...',
            'aria-label': 'Buscar'
        })
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(activa=True),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    orden = forms.ChoiceField(
        choices=[
            ('recientes', 'Más recientes'),
            ('precio_asc', 'Precio: menor a mayor'),
            ('precio_desc', 'Precio: mayor a menor'),
            ('titulo', 'Título A-Z'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ContactoForm(forms.Form):
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Tu correo electrónico'})
    )
    asunto = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Asunto'})
    )
    mensaje = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Tu mensaje'})
    )
