# usuarios/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Empresa
from ventas.models import Cliente  # Asegurate de que esté definido ahí

from .forms import UsuarioCreationForm, UsuarioChangeForm

class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = Usuario

    list_display = ('username', 'email', 'empresa', 'is_staff', 'is_active')

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('empresa',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'empresa'),
        }),
    )

admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Empresa)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cuit', 'condicion_iva')
    search_fields = ('nombre', 'cuit')