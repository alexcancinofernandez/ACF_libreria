from django import forms
from .models import Libro, Usuario

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")

    class Meta:
        model = Usuario
        fields = ['email', 'username', 'telefono']
        labels = {
            'email': 'Correo electrónico',
            'username': 'Nombre de usuario',
            'telefono': 'Teléfono (opcional)',
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get("password")
        password_confirm = self.cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['username', 'telefono', 'direccion_envio']
        labels = {
            'username': 'Nombre de usuario',
            'telefono': 'Teléfono',
            'direccion_envio': 'Dirección de envío',
        }

class LibroForm(forms.ModelForm):
    class Meta:
        model = Libro
        exclude = ('tamanio_archivo', 'fecha_creacion', 'fecha_actualizacion', 'creado_por')
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'meta_descripcion': forms.Textarea(attrs={'rows': 2}),
        }
