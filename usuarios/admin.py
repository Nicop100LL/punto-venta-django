from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Empresa
from ventas.models import Cliente, ReglaArcaPago, ComprobanteArca, TokenArca
from .forms import UsuarioCreationForm, UsuarioChangeForm


class ReglaArcaPagoInline(admin.TabularInline):
    model = ReglaArcaPago
    extra = 0
    fields = ("tipo_pago", "subir_a_arca", "tipo_comprobante")
    verbose_name = "Regla de facturación"
    verbose_name_plural = "Reglas por tipo de pago"


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cuit", "usa_arca", "arca_modo", "arca_punto_venta")
    list_editable = ("usa_arca",)
    fieldsets = (
        ("Datos generales", {
            "fields": ("nombre", "cuit", "direccion", "condicion_iva", "logo", "formato_ticket", "activo")
        }),
        ("Configuración ARCA", {
            "fields": (
                "usa_arca",
                "arca_modo",
                "arca_punto_venta",
                "arca_certificado",
                "arca_clave_privada",
            ),
            "classes": ("collapse",),
            "description": "Completar solo si la empresa factura con ARCA."
        }),
    )
    inlines = [ReglaArcaPagoInline]


@admin.action(description="Reintentar comprobantes en error")
def reintentar_comprobantes(modeladmin, request, queryset):
    actualizados = 0
    omitidos = 0
    for comp in queryset:
        if comp.estado == "error" and comp.puede_reintentar():
            comp.estado = "pendiente"
            comp.mensaje_error = None
            comp.save(update_fields=["estado", "mensaje_error"])
            actualizados += 1
        else:
            omitidos += 1
    modeladmin.message_user(
        request,
        f"{actualizados} comprobante(s) marcados para reintento. "
        f"{omitidos} omitido(s) (no estaban en error o alcanzaron el máximo de intentos)."
    )


@admin.register(ComprobanteArca)
class ComprobanteArcaAdmin(admin.ModelAdmin):
    list_display = ("venta", "tipo", "estado", "cae", "intentos", "ultimo_intento", "creado_en")
    list_filter = ("estado", "tipo")
    readonly_fields = ("cae", "vencimiento_cae", "enviado_en", "raw_response", "creado_en", "ultimo_intento")
    search_fields = ("venta__id", "cae")
    actions = [reintentar_comprobantes]


class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = Usuario
    list_display = ('username', 'email', 'empresa', 'is_staff', 'is_active', 'es_empleado')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('empresa', 'es_empleado')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'empresa', 'es_empleado'),
        }),
    )


admin.site.register(Usuario, UsuarioAdmin)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cuit', 'condicion_iva')
    search_fields = ('nombre', 'cuit')
    

@admin.register(TokenArca)
class TokenArcaAdmin(admin.ModelAdmin):
    list_display = ("empresa", "servicio", "modo", "expira", "creado_en")
    readonly_fields = ("token", "sign", "expira", "creado_en")    