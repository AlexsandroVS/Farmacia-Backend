from datetime import datetime
from decimal import Decimal
from io import BytesIO
from reportlab.lib import colors

# Django imports
from django.views import View
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string, get_template
from django.shortcuts import get_object_or_404, render
from django.db.models import Sum, Count, ExpressionWrapper, F, DecimalField
from django.contrib.auth.models import User

# DRF imports
from rest_framework import viewsets, status, generics
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

# Otros
from xhtml2pdf import pisa
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from .models import (
    DetalleFactura, DetalleFacturaCliente, FacturaCliente, Persona, Empleado, Clientes, Proveedor,
    Categoria, Producto, Medicamento, Factura, Pedidos, 
)
from .serializers import (
    FacturaClienteSerializer, PersonaSerializer, EmpleadoSerializer, ClientesSerializer, ProveedorSerializer,
    CategoriaSerializer, ProductoSerializer, MedicamentoSerializer, FacturaSerializer,
    PedidosSerializer, UserSerializer, ProveedorTopSerializer,
)
@api_view(['GET'])
def proveedores_top_view(request):
    try:
        # Obtener los proveedores con el total de sus pedidos sumados y el conteo de pedidos
        proveedores = (
            Proveedor.objects
            .annotate(
                total_pedidos=Sum('pedidos__total_pedido'),  # Sumar el total de los pedidos
                cantidad_pedidos=Count('pedidos')  # Contar cuántos pedidos tiene el proveedor
            )
            .filter(total_pedidos__gt=0)  # Filtrar solo proveedores con pedidos
            .order_by('-total_pedidos')  # Ordenar de mayor a menor según el total de pedidos
        )

        proveedores_top = proveedores[:10]  # Limitar a los primeros 10 proveedores

        # Crear la respuesta con la información de los proveedores
        data = [
            {   'id': proveedor.id,
                'nombre': proveedor.nombre,
                'total_pedido': proveedor.total_pedidos,
                'cantidad_pedidos': proveedor.cantidad_pedidos,
            }
            for proveedor in proveedores_top
        ]

        return Response(data)

    except Exception as e:
        # En caso de error, devolver un mensaje
        return Response({'error': str(e)}, status=500)

from django.db.models import Sum
from django.http import JsonResponse
from .models import Producto, DetalleFactura

class ProductosMasVendidosAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Obtener los productos más vendidos sumando la cantidad vendida en cada detalle de factura
        productos_mas_vendidos = (
            DetalleFactura.objects
            .values('producto')
            .annotate(total_vendido=Sum('cantidad'))  # Sumar la cantidad vendida de cada producto
            .order_by('-total_vendido')  # Ordenar de mayor a menor por cantidad vendida
        )
        
        # Obtener los productos correspondientes a los resultados
        productos = []
        for detalle in productos_mas_vendidos:
            producto = Producto.objects.get(id=detalle['producto'])
            productos.append(producto)
        
        # Serializar los productos
        serializer = ProductoSerializer(productos, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_superuser(request):
    user = request.user
    return Response({"is_superuser": user.is_superuser})
class RegisterClienteView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ClientesSerializer(data=request.data)
        if serializer.is_valid():
            cliente = serializer.save()
            return Response({"message": "Cliente creado correctamente!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Recuperar el cliente asociado al usuario
        try:
            cliente = Clientes.objects.get(user=user)
        except Clientes.DoesNotExist:
            return Response({"error": "Cliente no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        # Devolver más datos del cliente
        return Response({
            "cliente_id": cliente.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "direccion": cliente.direccion,
            "dni": cliente.dni,
        }, status=status.HTTP_200_OK)

class CurrentUserManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Devolver los datos básicos del usuario autenticado
        return Response({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }, status=status.HTTP_200_OK)
    
class ProductoPorCategoriaView(APIView):
    def get(self, request, categoria_id, *args, **kwargs):
        productos = Producto.objects.filter(categoria_id=categoria_id)
        if productos.exists():
            serializer = ProductoSerializer(productos, many=True, context={'request': request})  # Pasar el contexto
            return Response(serializer.data)
        return Response({"error": "No se encontraron productos para esta categoría."}, status=status.HTTP_404_NOT_FOUND)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer

class EmpleadoViewSet(viewsets.ModelViewSet):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Clientes.objects.all()
    serializer_class = ClientesSerializer

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        categoria_id = self.request.query_params.get('categoria_id', None)
        if categoria_id is not None:
            queryset = queryset.filter(categoria_id=categoria_id)
        return queryset

class MedicamentoViewSet(viewsets.ModelViewSet):
    queryset = Medicamento.objects.all()
    serializer_class = MedicamentoSerializer
    lookup_field = 'id'

class MedicamentoDetailView(RetrieveAPIView):
    queryset = Medicamento.objects.select_related('producto')
    serializer_class = MedicamentoSerializer    

class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer

    def create(self, request, *args, **kwargs):
        factura_data = request.data

        try:
            # Obtener el empleado y cliente
            empleado = Empleado.objects.get(id=factura_data["empleado"])
            cliente_nombre = factura_data["cliente"]  # Nombre del cliente como string

            # Crear la factura inicial
            factura = Factura.objects.create(
                empleado=empleado,
                cliente=cliente_nombre,
                fecha=factura_data["fecha"]
            )

            # Crear los detalles de la factura y calcular el total
            total = Decimal(0)
            for detalle in factura_data["detalles"]:
                producto = Producto.objects.get(id=detalle["producto"])
                cantidad_vendida = detalle["cantidad"]

                # Calcular subtotal del detalle (precio unitario con IGV * cantidad)
                subtotal_detalle = producto.precio * Decimal(cantidad_vendida)
                total += subtotal_detalle

                # Crear detalle de factura
                DetalleFactura.objects.create(
                    factura=factura,
                    producto=producto,
                    cantidad=cantidad_vendida,
                    precio_unitario=producto.precio,  # Precio con IGV
                    subtotal=subtotal_detalle
                )

                # Actualizar el stock del producto
                producto.stock -= cantidad_vendida
                producto.save()

            # Calcular IGV y total
            igv = total * Decimal(0.18)
            subtotal = total - igv

            # Actualizar los valores en la factura
            factura.subtotal = subtotal
            factura.igv = igv
            factura.total = total
            factura.save()

            # Serializar la factura
            serializer = FacturaSerializer(factura)

            # Agregar el nombre del empleado en los datos de la respuesta
            factura_data = serializer.data
            factura_data['empleado_nombre'] = empleado.persona.nombre  # Incluyendo el nombre del empleado

            return Response(factura_data, status=status.HTTP_201_CREATED)

        except Empleado.DoesNotExist:
            return Response({"error": "Empleado no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
        except Producto.DoesNotExist:
            return Response({"error": "Producto no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FacturaClienteViewSet(viewsets.ModelViewSet):
    queryset = FacturaCliente.objects.all()
    serializer_class = FacturaClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            # Retornar todas las facturas si es superusuario
            return FacturaCliente.objects.all()
        else:
            # Retornar solo las facturas del cliente autenticado
            return FacturaCliente.objects.filter(cliente=user)

    def create(self, request, *args, **kwargs):
        cliente = request.user.clientes  # Obtener el cliente relacionado al usuario
        factura_data = request.data

        try:
            # Crear factura inicial
            factura_cliente = FacturaCliente.objects.create(
                cliente=request.user,
                subtotal=0,
                igv=0,
                total=0
            )

            total = Decimal(0)
            for detalle in factura_data["detalles"]:
                producto = Producto.objects.get(id=detalle["producto"])
                cantidad = detalle["cantidad"]

                if producto.stock < cantidad:
                    return Response(
                        {"error": f"Stock insuficiente para el producto {producto.nombre}. Quedan {producto.stock} unidades."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                subtotal = producto.precio * Decimal(cantidad)
                total += subtotal

                # Crear detalle
                DetalleFacturaCliente.objects.create(
                    factura=factura_cliente,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                    subtotal=subtotal
                )

                # Reducir el stock
                producto.stock -= cantidad
                producto.save()

            igv = total * Decimal(0.18)
            subtotal_factura = total - igv

            # Actualizar la factura
            factura_cliente.subtotal = subtotal_factura
            factura_cliente.igv = igv
            factura_cliente.total = total
            factura_cliente.save()

            serializer = FacturaClienteSerializer(factura_cliente, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Producto.DoesNotExist:
            return Response({"error": "Producto no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PedidosViewSet(ModelViewSet):
    queryset = Pedidos.objects.all()
    serializer_class = PedidosSerializer

    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
       
        pedido = self.get_object()
        estado_anterior = pedido.estado
        nuevo_estado = request.data.get('estado')

        if nuevo_estado and nuevo_estado != estado_anterior:
            pedido.estado = nuevo_estado
            pedido.save()
            return Response({
                "mensaje": "Estado actualizado correctamente",
                "estado_anterior": estado_anterior,
                "nuevo_estado": nuevo_estado
            })
        return Response({
            "error": "No se pudo actualizar el estado. Verifica los datos enviados."
        }, status=400)

def landing_page(request):
    return render(request, 'landing.html')
@api_view(['PUT'])
def actualizar_pedido(request, pk):
    try:
        pedido = Pedidos.objects.get(pk=pk)
    except Pedidos.DoesNotExist:
        return Response({"detail": "Pedido no encontrado"}, status=404)

    # Obtener el estado enviado en el request
    estado = request.data.get('estado')
    cantidad = request.data.get('cantidad')  # Asegurarse de obtener la cantidad
    if cantidad:
        cantidad = int(cantidad)  # Convertir a entero

    # Actualizar el estado del pedido
    pedido.estado = estado

    if estado == 'Completado':
        # Obtener el producto relacionado con el pedido
        producto = pedido.producto
        print(f"Producto antes de actualizar stock: {producto.nombre}, stock actual: {producto.stock}")

        # Verificar si hay suficiente stock
        if producto.stock >= cantidad:
            producto.stock -= cantidad
            producto.save()  # Guardar el producto con el stock actualizado
            print(f"Producto actualizado: {producto.nombre}, nuevo stock: {producto.stock}")
        else:
            return Response({"detail": "Stock insuficiente para completar el pedido"}, status=400)

    pedido.save()

    return Response({"detail": "Pedido actualizado con éxito", "pedido": pedido.id}, status=200)

def generar_factura_pdf(request, factura_id):
    try:
        # Obtener la factura y los detalles relacionados
        factura = Factura.objects.get(id=factura_id)
        detalles = DetalleFactura.objects.filter(factura=factura)

        # Obtener el cliente
        cliente = factura.cliente

        # Obtener el nombre completo del cliente desde el modelo 'User'
        nombre_cliente = f"{cliente.user.first_name} {cliente.user.last_name}"

        # Contexto para la plantilla
        context = {
            "factura": factura,
            "detalles": detalles,
            "nombre_cliente": nombre_cliente,
            "numero_pedido": factura.id,  # El número de pedido es el ID de la factura
            "direccion_cliente": cliente.direccion,
            "dni_cliente": cliente.dni
        }

        # Renderizar plantilla HTML
        template = get_template("factura_pdf.html")  # Asegúrate de crear esta plantilla
        html = template.render(context)

        # Crear el archivo PDF
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename=factura_{factura.id}.pdf"
        pisa_status = pisa.CreatePDF(html, dest=response)

        # Manejar errores en la generación del PDF
        if pisa_status.err:
            return HttpResponse("Error al generar el PDF", status=500)

        return response
    except Factura.DoesNotExist:
        return HttpResponse("Factura no encontrada", status=404)

@api_view(['GET'])
def reporte_general(request):
    try:
        # Verificar si la solicitud es para un PDF
        if request.GET.get('format') == 'pdf':
            # Generación del PDF
            facturas = Factura.objects.all()
            total_facturas = facturas.aggregate(total_facturado=Sum('total'))['total_facturado'] or 0.0
            total_igv = facturas.aggregate(total_igv=Sum('igv'))['total_igv'] or 0.0
            total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0.0

            # Resumen de productos más vendidos
            productos_vendidos = Factura.objects.values('detalles__producto').annotate(
                total_vendido=Sum('detalles__cantidad')
            ).order_by('-total_vendido')[:5]

            productos_data = []
            for producto_data in productos_vendidos:
                try:
                    producto = Producto.objects.get(id=producto_data['detalles__producto'])
                    producto_serializer = ProductoSerializer(producto)
                    productos_data.append({
                        'producto': producto_serializer.data,
                        'total_vendido': producto_data['total_vendido']
                    })
                except Producto.DoesNotExist:
                    continue

            # Renderizar el template para el PDF
            html = render_to_string('reporte_general_pdf.html', {
                'total_facturado': total_facturas,
                'total_igv': total_igv,
                'total_subtotal': total_subtotal,
                'productos_vendidos': productos_data,
            })

            # Crear respuesta de PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="reporte_general.pdf"'

            # Generar PDF con xhtml2pdf
            pisa_status = pisa.CreatePDF(html, dest=response)

            if pisa_status.err:
                return HttpResponse("Error al generar el PDF", status=500)

            return response
        
        # Si no se requiere PDF, retornar los datos en formato JSON
        facturas = Factura.objects.all()
        total_facturas = facturas.aggregate(total_facturado=Sum('total'))['total_facturado'] or 0.0
        total_igv = facturas.aggregate(total_igv=Sum('igv'))['total_igv'] or 0.0
        total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0.0

        productos_vendidos = Factura.objects.values('detalles__producto').annotate(
            total_vendido=Sum('detalles__cantidad')
        ).order_by('-total_vendido')[:5]

        productos_data = []
        for producto_data in productos_vendidos:
            try:
                producto = Producto.objects.get(id=producto_data['detalles__producto'])
                producto_serializer = ProductoSerializer(producto)
                productos_data.append({
                    'producto': producto_serializer.data,
                    'total_vendido': producto_data['total_vendido']
                })
            except Producto.DoesNotExist:
                continue

        proveedores = Proveedor.objects.all()
        proveedores_top = ProveedorTopSerializer(proveedores, many=True)

        pedidos = Pedidos.objects.all()
        total_pedidos = pedidos.aggregate(total_pedidos=Sum('total_pedido'))['total_pedidos'] or 0.0
        total_pedidos_count = pedidos.count()

        reporte_data = {
            'total_facturado': total_facturas,
            'total_igv': total_igv,
            'total_subtotal': total_subtotal,
            'productos_vendidos': productos_data,
            'proveedores': proveedores_top.data,
            'total_pedidos': total_pedidos,
            'total_pedidos_count': total_pedidos_count
        }

        return Response(reporte_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def reporte_mensual(request, year, month):
    # Filtrar las facturas por el año y mes proporcionados
    facturas = Factura.objects.filter(fecha__year=year, fecha__month=month)
    
    # Calcular el total de ventas y el IGV
    ventas_totales = facturas.aggregate(total_ventas=Sum('total'))['total_ventas'] or 0
    total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0
    total_igv = ventas_totales - total_subtotal
    
    ventas_totales = round(ventas_totales, 2)
    total_subtotal = round(total_subtotal, 2)
    total_igv = round(total_igv, 2)
    
    # Obtener los detalles de las ventas
    detalles_ventas = DetalleFactura.objects.filter(factura__in=facturas)
    
    # Obtener las ventas por producto con más detalles
    ventas_por_producto = detalles_ventas.values('producto').annotate(
        cantidad_vendida=Sum('cantidad'),
        subtotal=Sum('subtotal')
    )
    
    productos_vendidos = []
    for venta in ventas_por_producto:
        producto = Producto.objects.get(id=venta['producto'])
        
        productos_vendidos.append({
            'producto': {
                'id': producto.id,
                'nombre': producto.nombre,
                'descripcion': producto.descripcion,
                'precio_sin_igv': str(producto.precio_sin_igv),
                'precio': str(producto.precio),
                'stock': producto.stock,
                'fecha_vencimiento': producto.fecha_vencimiento.strftime('%Y-%m-%d'),
                'presentacion': producto.presentacion,
                'categoria': producto.categoria.id,
                'categoria_nombre': producto.categoria.nombre,
                'proveedor': producto.proveedor.id,
                'proveedor_nombre': producto.proveedor.nombre,
                'imagen': producto.imagen.url if producto.imagen else None,
                'imagen_url': producto.imagen.url if producto.imagen else None
            },
            'total_vendido': venta['cantidad_vendida']
        })
    
    # Filtrar los pedidos por el año y mes proporcionados
    pedidos = Pedidos.objects.filter(fecha_pedido__year=year, fecha_pedido__month=month)

    
    # Obtener proveedores con su total de pedidos y monto facturado
    proveedores = Proveedor.objects.all()
    proveedores_info = []
    for proveedor in proveedores:
        total_pedidos_mes = pedidos.aggregate(total_pedidos=Sum('total_pedido'))['total_pedidos'] or 0.0
        monto_total = facturas.filter(detalles__producto__proveedor=proveedor).aggregate(monto_total=Sum('total'))['monto_total'] or 0
        
        proveedores_info.append({
            'id': proveedor.id,
            'nombre': proveedor.nombre,
            'total_pedidos_mes': total_pedidos_mes,
            'monto_total': str(monto_total)
        })
    
    # Crear el diccionario con todos los datos
    response_data = {
        'total_facturado': str(ventas_totales),
        'total_igv': str(total_igv),
        'total_subtotal': str(total_subtotal),
        'productos_vendidos': productos_vendidos,
        'proveedores': proveedores_info,
        'total_pedidos_mes': total_pedidos_mes,
        'total_pedidos_count': facturas.count(),  # Cantidad de facturas
        'year': year,
        'month': month,
        'nombre_mes': datetime(year, month, 1).strftime('%B')
    }
    
    return JsonResponse(response_data)

def reporte_mensualpdf(request, year, month):
    # Filtrar las facturas por el año y mes proporcionados
    facturas = Factura.objects.filter(fecha__year=year, fecha__month=month)
    
    # Calcular el total de ventas y el IGV
    ventas_totales = facturas.aggregate(total_ventas=Sum('total'))['total_ventas'] or 0
    total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0
    total_igv = ventas_totales - total_subtotal
    
    ventas_totales = round(ventas_totales, 2)
    total_subtotal = round(total_subtotal, 2)
    total_igv = round(total_igv, 2)
    
    # Obtener los detalles de las ventas
    detalles_ventas = DetalleFactura.objects.filter(factura__in=facturas)
    
    # Obtener las ventas por producto con más detalles
    ventas_por_producto = detalles_ventas.values('producto').annotate(
        cantidad_vendida=Sum('cantidad'),
        subtotal=Sum('subtotal')
    )
    
    productos_vendidos = []
    for venta in ventas_por_producto:
        producto = Producto.objects.get(id=venta['producto'])
        productos_vendidos.append({
            'producto': {
                'id': producto.id,
                'nombre': producto.nombre,
                'descripcion': producto.descripcion,
                'precio_sin_igv': str(producto.precio_sin_igv),
                'precio': str(producto.precio),
            },
            'total_vendido': venta['cantidad_vendida']
        })
    
    # Crear el contexto que se pasará al template
    context = {
        'ventas_totales': ventas_totales,
        'total_igv': total_igv,
        'total_subtotal': total_subtotal,
        'productos_vendidos': productos_vendidos,
        'year': year,
        'month': month,
        'nombre_mes': datetime(year, month, 1).strftime('%B'),
    }

    # Renderizar el contenido HTML usando un template
    html_content = render_to_string('reporte_mensual.html', context)

    # Crear la respuesta HTTP con el tipo de contenido PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_mensual.pdf"'
    
    # Convertir el HTML a PDF
    pisa_status = pisa.CreatePDF(html_content, dest=response)

    # Verificar si se generó correctamente el PDF
    if pisa_status.err:
        return HttpResponse("Hubo un error al generar el PDF", status=500)

    return response

@api_view(['GET'])
def reporte_general_clientes(request):
    try:
        # Verificar si la solicitud es para un PDF
        if request.GET.get('format') == 'pdf':
            # Generación del PDF
            facturas = FacturaCliente.objects.all()
            total_facturas = facturas.aggregate(total_facturado=Sum('total'))['total_facturado'] or 0.0
            total_igv = facturas.aggregate(total_igv=Sum('igv'))['total_igv'] or 0.0
            total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0.0

            # Resumen de productos más vendidos
            productos_vendidos = FacturaCliente.objects.values('detalles__producto').annotate(
                total_vendido=Sum('detalles__cantidad')
            ).order_by('-total_vendido')[:5]

            productos_data = []
            for producto_data in productos_vendidos:
                try:
                    producto = Producto.objects.get(id=producto_data['detalles__producto'])
                    producto_serializer = ProductoSerializer(producto)
                    productos_data.append({
                        'producto': producto_serializer.data,
                        'total_vendido': producto_data['total_vendido']
                    })
                except Producto.DoesNotExist:
                    continue

            # Renderizar el template para el PDF
            html = render_to_string('reporte_general_pdf.html', {
                'total_facturado': total_facturas,
                'total_igv': total_igv,
                'total_subtotal': total_subtotal,
                'productos_vendidos': productos_data,
            })

            # Crear respuesta de PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="reporte_general.pdf"'

            # Generar PDF con xhtml2pdf
            pisa_status = pisa.CreatePDF(html, dest=response)

            if pisa_status.err:
                return HttpResponse("Error al generar el PDF", status=500)

            return response
        
        # Si no se requiere PDF, retornar los datos en formato JSON
        facturas = FacturaCliente.objects.all()
        total_facturas = facturas.aggregate(total_facturado=Sum('total'))['total_facturado'] or 0.0
        total_igv = facturas.aggregate(total_igv=Sum('igv'))['total_igv'] or 0.0
        total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0.0

        productos_vendidos = FacturaCliente.objects.values('detalles__producto').annotate(
            total_vendido=Sum('detalles__cantidad')
        ).order_by('-total_vendido')[:5]

        productos_data = []
        for producto_data in productos_vendidos:
            try:
                producto = Producto.objects.get(id=producto_data['detalles__producto'])
                producto_serializer = ProductoSerializer(producto)
                productos_data.append({
                    'producto': producto_serializer.data,
                    'total_vendido': producto_data['total_vendido']
                })
            except Producto.DoesNotExist:
                continue

        reporte_data = {
            'total_facturado': total_facturas,
            'total_igv': total_igv,
            'total_subtotal': total_subtotal,
            'productos_vendidos': productos_data,
        }

        return Response(reporte_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def reporte_mensual_clientes(request, year, month):
    # Filtrar las facturas por el año y mes proporcionados
    facturas = FacturaCliente.objects.filter(fecha__year=year, fecha__month=month)
    
    # Calcular el total de ventas y el IGV
    ventas_totales = facturas.aggregate(total_ventas=Sum('total'))['total_ventas'] or 0
    total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0
    total_igv = ventas_totales - total_subtotal
    
    ventas_totales = round(ventas_totales, 2)
    total_subtotal = round(total_subtotal, 2)
    total_igv = round(total_igv, 2)
    
    # Obtener los detalles de las ventas
    detalles_ventas = DetalleFacturaCliente.objects.filter(factura__in=facturas)
    
    # Obtener las ventas por producto con más detalles
    ventas_por_producto = detalles_ventas.values('producto').annotate(
        cantidad_vendida=Sum('cantidad'),
        subtotal=Sum('subtotal')
    )
    
    productos_vendidos = []
    for venta in ventas_por_producto:
        producto = Producto.objects.get(id=venta['producto'])
        
        productos_vendidos.append({
            'producto': {
                'id': producto.id,
                'nombre': producto.nombre,
                'descripcion': producto.descripcion,
                'precio_sin_igv': str(producto.precio_sin_igv),
                'precio': str(producto.precio),
                'stock': producto.stock,
                'fecha_vencimiento': producto.fecha_vencimiento.strftime('%Y-%m-%d'),
                'presentacion': producto.presentacion,
                'categoria': producto.categoria.id,
                'categoria_nombre': producto.categoria.nombre,
                'proveedor': producto.proveedor.id,
                'proveedor_nombre': producto.proveedor.nombre,
                'imagen': producto.imagen.url if producto.imagen else None,
                'imagen_url': producto.imagen.url if producto.imagen else None
            },
            'total_vendido': venta['cantidad_vendida']
        })
    
    response_data = {
        'total_facturado': str(ventas_totales),
        'total_igv': str(total_igv),
        'total_subtotal': str(total_subtotal),
        'productos_vendidos': productos_vendidos,
        'year': year,
        'month': month,
        'nombre_mes': datetime(year, month, 1).strftime('%B')
    }
    
    return JsonResponse(response_data)

def reporte_mensual_pdf(request, year, month):
    try:
        # Filtrar las facturas por el año y mes proporcionados
        facturas = FacturaCliente.objects.filter(fecha__year=year, fecha__month=month)
        
        # Calcular el total de ventas y el IGV
        ventas_totales = facturas.aggregate(total_ventas=Sum('total'))['total_ventas'] or 0
        total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0
        total_igv = ventas_totales - total_subtotal
        
        ventas_totales = round(ventas_totales, 2)
        total_subtotal = round(total_subtotal, 2)
        total_igv = round(total_igv, 2)
        
        # Obtener los detalles de las ventas
        detalles_ventas = DetalleFacturaCliente.objects.filter(factura__in=facturas)
        
        # Obtener las ventas por producto con más detalles
        ventas_por_producto = detalles_ventas.values('producto').annotate(
            cantidad_vendida=Sum('cantidad'),
            subtotal=Sum('subtotal')
        )
        
        productos_vendidos = []
        for venta in ventas_por_producto:
            producto = Producto.objects.get(id=venta['producto'])
            
            productos_vendidos.append({
                'producto': {
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'descripcion': producto.descripcion,
                    'precio_sin_igv': str(producto.precio_sin_igv),
                    'precio': str(producto.precio),
                    'stock': producto.stock,
                    'fecha_vencimiento': producto.fecha_vencimiento.strftime('%Y-%m-%d'),
                    'presentacion': producto.presentacion,
                    'categoria': producto.categoria.id,
                    'categoria_nombre': producto.categoria.nombre,
                    'proveedor': producto.proveedor.id,
                    'proveedor_nombre': producto.proveedor.nombre,
                    'imagen': producto.imagen.url if producto.imagen else None,
                    'imagen_url': producto.imagen.url if producto.imagen else None
                },
                'total_vendido': venta['cantidad_vendida']
            })
        
        # Crear el contexto para el template del PDF
        context = {
            'total_facturado': ventas_totales,
            'total_igv': total_igv,
            'total_subtotal': total_subtotal,
            'productos_vendidos': productos_vendidos,
            'year': year,
            'month': month,
            'nombre_mes': datetime(year, month, 1).strftime('%B'),
            'current_date': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        }
        
        # Renderizar el template para el PDF
        html = render_to_string('reporte_mensual_pdf.html', context)
        
        # Crear la respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_mensual_{year}_{month}.pdf"'
        
        # Generar el PDF con xhtml2pdf
        pisa_status = pisa.CreatePDF(html, dest=response)
        
        # Si hubo algún error en la generación del PDF, manejarlo
        if pisa_status.err:
            return HttpResponse("Error al generar el PDF", status=500)
        
        return response

    except Exception as e:
        return HttpResponse(f"Error al generar el reporte PDF: {e}", status=500)
@api_view(['GET'])
def descargar_reporte_general(request):
    try:
        # Obtener los datos para el reporte
        facturas = Factura.objects.all()
        total_facturas = facturas.aggregate(total_facturado=Sum('total'))['total_facturado'] or Decimal('0.0')
        total_igv = facturas.aggregate(total_igv=Sum('igv'))['total_igv'] or Decimal('0.0')
        total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or Decimal('0.0')

        productos_vendidos = Factura.objects.values('detalles__producto').annotate(
            total_vendido=Sum('detalles__cantidad')
        ).order_by('-total_vendido')[:5]
        
        productos_data = []
        for producto_data in productos_vendidos:
            try:
                producto = Producto.objects.get(id=producto_data['detalles__producto'])
                precio_unitario = Decimal(producto.precio)
                cantidad_vendida = Decimal(producto_data['total_vendido'])
                igv = (precio_unitario * cantidad_vendida * Decimal('0.18')).quantize(Decimal('0.01'))
                total = (precio_unitario * cantidad_vendida * Decimal('1.18')).quantize(Decimal('0.01'))
                producto_serializer = ProductoSerializer(producto)
                productos_data.append({
                    'producto': producto_serializer.data,
                    'total_vendido': cantidad_vendida,
                    'igv': igv,
                    'total': total
                })
            except Producto.DoesNotExist:
                continue

        proveedores = Proveedor.objects.all()
        proveedores_top = ProveedorTopSerializer(proveedores, many=True)

        pedidos = Pedidos.objects.all()
        total_pedidos = pedidos.aggregate(total_pedidos=Sum('total_pedido'))['total_pedidos'] or Decimal('0.0')
        total_pedidos_count = pedidos.count()

        # Cálculo de la ganancia neta
        ganancia_neta = (total_subtotal - total_pedidos).quantize(Decimal('0.01'))

        reporte_data = {
            'total_facturado': total_facturas,
            'total_igv': total_igv,
            'total_subtotal': total_subtotal,
            'productos_vendidos': productos_data,
            'proveedores': proveedores_top.data,
            'total_pedidos': total_pedidos,
            'total_pedidos_count': total_pedidos_count,
            'ganancia_neta': ganancia_neta,
        }

        # Generar el PDF
        template = get_template('reporte_general.html')
        html = template.render({'reporte': reporte_data})

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_general.pdf"'

        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return Response({'error': 'Error al generar el PDF'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def generar_pdf_factura(request, factura_id):
    try:
        # Obtén la factura con los detalles
        factura = Factura.objects.get(id=factura_id)
        detalles = factura.detalles.all()

        # Renderiza el HTML como texto para mostrarlo en el PDF
        html_content = render_to_string('factura_template.html', {'factura': factura, 'detalles': detalles})

        # Crea un buffer para almacenar el PDF generado
        buffer = BytesIO()

        # Usa xhtml2pdf para convertir el HTML al PDF
        pisa_status = pisa.CreatePDF(html_content, dest=buffer)

        # Verifica si hubo algún error al generar el PDF
        if pisa_status.err:
            return HttpResponse("Error al generar el PDF", status=500)

        # Reajusta el buffer a la posición inicial para la respuesta HTTP
        buffer.seek(0)

        # Crea la respuesta HTTP con el PDF generado
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="factura_{factura.id}.pdf"'

        return response

    except Factura.DoesNotExist:
        return HttpResponse("Factura no encontrada", status=404)
    except Exception as e:
        return HttpResponse(f"Error al generar el PDF: {str(e)}", status=500)

@api_view(['GET'])
def generar_reporte_pdf_cliente(request):
    try:
        # Obtener las facturas y realizar los cálculos
        facturas = FacturaCliente.objects.all()
        total_facturado = facturas.aggregate(total_facturado=Sum('total'))['total_facturado'] or 0.0
        total_igv = facturas.aggregate(total_igv=Sum('igv'))['total_igv'] or 0.0
        total_subtotal = facturas.aggregate(total_subtotal=Sum('subtotal'))['total_subtotal'] or 0.0

        # Redondear los valores a 2 decimales
        total_facturado = round(total_facturado, 2)
        total_igv = round(total_igv, 2)
        total_subtotal = round(total_subtotal, 2)

        # Productos más vendidos
        productos_vendidos = DetalleFacturaCliente.objects.values('producto').annotate(
            total_vendido=Sum('cantidad')
        ).order_by('-total_vendido')[:5]

        productos_data = []
        for producto_data in productos_vendidos:
            try:
                producto = Producto.objects.get(id=producto_data['producto'])
                productos_data.append({
                    'producto_id': producto.id,
                    'producto_nombre': producto.nombre,
                    'producto_precio': round(producto.precio, 2),  # Redondear el precio
                    'total_vendido': producto_data['total_vendido'],
                })
            except Producto.DoesNotExist:
                continue

        # Renderizar el template para el PDF
        html = render_to_string('reporte_general_pdf.html', {
            'total_facturado': total_facturado,
            'total_igv': total_igv,
            'total_subtotal': total_subtotal,
            'productos_vendidos': productos_data,
        })

        # Crear respuesta de PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_general_clientes.pdf"'

        # Generar PDF con xhtml2pdf
        pisa_status = pisa.CreatePDF(html, dest=response)

        if pisa_status.err:
            return HttpResponse("Error al generar el PDF", status=500)

        return response
    except Exception as e:
        return HttpResponse(f"Error al generar el reporte: {e}", status=500)

def generar_pdf_factura_cliente(request, factura_id):
    try:
        # Obtén la factura de cliente con los detalles
        factura_cliente = FacturaCliente.objects.get(id=factura_id)
        detalles = factura_cliente.detalles.all()

        # Obtener los datos del cliente
        cliente = factura_cliente.cliente
        cliente_data = {
            'nombre': f"{cliente.first_name} {cliente.last_name}",
            'email': cliente.email,
              
            
        }

        # Renderiza el HTML con el template y los datos de la factura
        html_content = render_to_string('factura_cliente_template.html', {
            'factura': factura_cliente,
            'detalles': detalles,
            'cliente': cliente_data,
        })

        # Crear un buffer de memoria para el PDF
        buffer = BytesIO()
        
        # Convertir el HTML a PDF usando xhtml2pdf
        pisa_status = pisa.CreatePDF(html_content, dest=buffer)

        if pisa_status.err:
            return HttpResponse("Error al generar el PDF", status=500)

        # Posiciona el puntero del buffer al principio
        buffer.seek(0)

        # Crear la respuesta HTTP con el PDF generado
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="factura_cliente_{factura_cliente.id}.pdf"'

        return response

    except FacturaCliente.DoesNotExist:
        return HttpResponse("Factura no encontrada", status=404)
    except Exception as e:
        return HttpResponse(f"Error al generar el PDF: {str(e)}", status=500)
    
