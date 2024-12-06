from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PersonaViewSet, EmpleadoViewSet, ClienteViewSet, ProductoPorCategoriaView, ProductosMasVendidosAPIView, ProveedorViewSet,
    CategoriaViewSet, ProductoViewSet, MedicamentoViewSet, RegisterView,
    FacturaViewSet, PedidosViewSet, CurrentUserView, check_superuser, generar_pdf_factura, generar_pdf_factura_cliente, generar_reporte_pdf_cliente,
    landing_page, RegisterClienteView, MedicamentoDetailView, proveedores_top_view, reporte_general, reporte_mensual, descargar_reporte_general, 
    FacturaClienteViewSet, CurrentUserManagementView, reporte_general_clientes, reporte_mensual_clientes,  reporte_mensualpdf
)

router = DefaultRouter()
router.register(r'personas', PersonaViewSet)
router.register(r'empleados', EmpleadoViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'proveedores', ProveedorViewSet)
router.register(r'categorias', CategoriaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'facturas-cliente', FacturaClienteViewSet, basename='factura-cliente')
router.register(r'medicamentos', MedicamentoViewSet)
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'pedidos', PedidosViewSet)

urlpatterns = [
    # Landing page
    path('', landing_page, name='landing_page'),  

    # API paths
    path('v1/', include(router.urls)),  
    path('v1/register/', RegisterView.as_view(), name='register'), 
    path('v1/current-managament/', CurrentUserManagementView.as_view(), name='current_managament'),
    path('v1/current-user/', CurrentUserView.as_view(), name='current_user'),
    
    # Reporte General
    path('v1/reporte-general/', reporte_general, name='reporte-general'),
    path('v1/reporte-general-pdf/', descargar_reporte_general, name='reporte-general-pdf'),
    
    # Reporte por cliente
    path('v1/reporte-general-cliente/', reporte_general_clientes, name='reporte-general_cliente'),
    path('v1/reporte-general-pdf-cliente/', generar_reporte_pdf_cliente, name='reporte_general_pdf_cliente'),
    path('v1/reporte-mensual-cliente/<int:year>/<int:month>/', reporte_mensual_clientes, name='reporte-mensual-cliente'),
    path('v1/reporte-mensual-pdf-cliente/<int:year>/<int:month>/', reporte_mensual_clientes, name='reporte_mensual_pdf_cliente'),

    # Reporte Mensual
    path('v1/reporte-mensual/<int:year>/<int:month>/', reporte_mensual, name='reporte-mensual'),
    path('v1/reporte-mensual-pdf/<int:year>/<int:month>/', reporte_mensualpdf, name='reporte_mensual_pdf'),

    # Register paths
    path('v1/register_cliente/', RegisterClienteView.as_view(), name='register_cliente'),
    
    # Producto and Medicamento details
    path('api/medicamentos/<int:pk>/', MedicamentoDetailView.as_view(), name='detalle_medicamento'),
    path('v1/productos/categoria/<int:categoria_id>/', ProductoPorCategoriaView.as_view(), name='productos_por_categoria'),

    # Factura paths
    path('factura/<int:factura_id>/pdf/', generar_pdf_factura, name='generar_pdf_factura'),
    path('factura_cliente/pdf/<int:factura_id>/', generar_pdf_factura_cliente, name='factura_cliente_pdf'),
    
    path('v1/productos-mas-vendidos/', ProductosMasVendidosAPIView.as_view(), name='productos_mas_vendidos'),


    
    # Superuser check
    path('auth/check-superuser/', check_superuser, name='check_superuser'),
    
    # Proveedor paths
    path('v1/proveedores-top/', proveedores_top_view, name='proveedores_top'),
]
