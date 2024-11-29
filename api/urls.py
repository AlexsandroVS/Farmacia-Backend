# v1/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
     PersonaViewSet, EmpleadoViewSet, ClienteViewSet, ProductoPorCategoriaView, ProveedorViewSet, 
    CategoriaViewSet, ProductoViewSet, MedicamentoViewSet, RegisterView,
    FacturaViewSet, PedidosViewSet,  CurrentUserView, generar_factura_pdf, 
    landing_page, RegisterClienteView, MedicamentoDetailView,  proveedores_top_view, reporte_general, ReporteMensualView, descargar_reporte_general
)

router = DefaultRouter()
router.register(r'personas', PersonaViewSet)
router.register(r'empleados', EmpleadoViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'proveedores', ProveedorViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'medicamentos', MedicamentoViewSet)
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'pedidos', PedidosViewSet)


urlpatterns = [
    path('', landing_page, name='landing_page'),  
    path('v1/', include(router.urls)),  
    path('v1/register/', RegisterView.as_view(), name='register'), 
    path('v1/current-user/', CurrentUserView.as_view(), name='current_user'),  
    path('v1/reporte-general/', reporte_general, name='reporte-general'),
    path('v1/reporte-general-pdf/', descargar_reporte_general, name='reporte-mensual-pdf'),
    path('reporte-mensual/', ReporteMensualView.as_view(), name='reporte-mensual'),
    path('v1/register_cliente/', RegisterClienteView.as_view(), name='register_cliente'),
    path('api/medicamentos/<int:pk>/', MedicamentoDetailView.as_view(), name='detalle_medicamento'),  
    path('v1/proveedores-top/', proveedores_top_view, name='proveedores_top'),
    path('v1/productos/categoria/<int:categoria_id>/', ProductoPorCategoriaView.as_view(), name='productos_por_categoria'),
    path('factura/<int:factura_id>/pdf/', generar_factura_pdf, name='generar_factura_pdf'),
]
