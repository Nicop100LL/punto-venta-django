from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth.forms import UsernameField
from .models import Usuario

class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'empresa')  # campos que realmente querés mostrar
        field_classes = {"username": UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer opcionales todos los campos adicionales que no quieras obligatorios
        optional_fields = ['first_name', 'last_name']  # agregar aquí otros campos opcionales si los hay
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False


class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'empresa', 'is_active', 'is_staff', 'is_superuser')
        field_classes = {"username": UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer opcionales los campos extra al editar
        optional_fields = ['first_name', 'last_name']
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False


class CustomAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                "Esta cuenta está inactiva.",
                code='inactive'
            )
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import Usuario
from django.contrib.auth.forms import UsernameField

class UsuarioCreationForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'empresa')
        field_classes = {"username": UsernameField}

class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'empresa', 'is_active', 'is_staff', 'is_superuser')
        field_classes = {"username": UsernameField}

class CustomAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError("Esta cuenta está inactiva.", code='inactive')
