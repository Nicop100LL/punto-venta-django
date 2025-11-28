from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Empresa
from ventas.models import Cliente
from .forms import UsuarioCreationForm, UsuarioChangeForm

class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = Usuario

    list_display = ('username', 'email', 'empresa', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'empresa')

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password', 'empresa')}),
        ('Permisos', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'empresa', 'is_staff', 'is_active'),
        }),
    )

    search_fields = ('username', 'email')
    ordering = ('username',)

admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Empresa)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cuit', 'condicion_iva')
    search_fields = ('nombre', 'cuit')
