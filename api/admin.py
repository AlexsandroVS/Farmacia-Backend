from django.contrib import admin
from .models import Producto,Clientes,Categoria,Empleado,Factura,Medicamento,Pedidos,Persona,Proveedor
# Register your models here


admin.site.register(Empleado)
admin.site.register(Factura)
admin.site.register(Pedidos)
admin.site.register(Medicamento)
admin.site.register(Proveedor)
admin.site.register(Categoria)
admin.site.register(Clientes)
admin.site.register(Producto)
admin.site.register(Persona)
