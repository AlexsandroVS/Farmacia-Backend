# api/views.py
from datetime import datetime
from decimal import Decimal

from django.views import View
from django.http import HttpResponse, JsonResponse
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.template.loader import get_template
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.generics import RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from django.db.models import Sum, Count, FloatField, ExpressionWrapper, F, DecimalField
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import (
    DetalleFactura, Persona, Empleado, Clientes, Proveedor,
    Categoria, Producto, Medicamento, Factura, Pedidos, 
)
from .serializers import (
    PersonaSerializer, EmpleadoSerializer, ClientesSerializer, ProveedorSerializer,
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

class ProveedoresTopView(APIView):
    def get(self, request, *args, **kwargs):
        # Aquí filtras los proveedores con más pedidos
        proveedores = Proveedor.objects.annotate(
            total_pedidos=Count('pedidos'),
            monto_total=Sum('pedidos__total_pedido')
        ).order_by('-total_pedidos')[:10]  # Por ejemplo, los top 10 proveedores

        serializer = ProveedorTopSerializer(proveedores, many=True)
        return Response(serializer.data)

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
        return Response({"nombre": user.username})
    
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
            empleado = Empleado.objects.get(id=factura_data["empleado"])
            cliente = Clientes.objects.get(id=factura_data["cliente"])
            
            # Crear factura inicial (sin calcular total)
            factura = Factura.objects.create(
                empleado=empleado,
                cliente=cliente,
                fecha=factura_data["fecha"]
            )

            # Crear los detalles de la factura
            for detalle in factura_data["detalles"]:
                producto = Producto.objects.get(id=detalle["producto"])
                DetalleFactura.objects.create(
                    factura=factura,
                    producto=producto,
                    cantidad=detalle["cantidad"],
                    precio_unitario=producto.precio,
                    subtotal=producto.precio * Decimal(detalle["cantidad"])  # Asegúrate de usar Decimal aquí
                )

            # Recalcular los totales de la factura (subtotal, IGV, total)
            subtotal = sum(detalle.subtotal for detalle in factura.detalles.all())
            igv = subtotal * Decimal(0.18)  # Convertir 0.18 a Decimal
            total = subtotal + igv

            # Actualizar los totales en la factura
            factura.subtotal = subtotal
            factura.igv = igv
            factura.total = total
            factura.save()

            # Serializar y devolver la respuesta
            serializer = FacturaSerializer(factura)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Empleado.DoesNotExist:
            return Response({"error": "Empleado no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
        except Clientes.DoesNotExist:
            return Response({"error": "Cliente no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
        except Producto.DoesNotExist:
            return Response({"error": "Producto no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
       
class PedidosViewSet(viewsets.ModelViewSet):
    queryset = Pedidos.objects.all()
    serializer_class = PedidosSerializer

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
        ganancia_neta = (total_facturas - total_pedidos).quantize(Decimal('0.01'))

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


class ReporteMensualView(View):
    def get(self, request, *args, **kwargs):
        mes = int(request.GET.get('mes', datetime.now().month))
        anio = int(request.GET.get('anio', datetime.now().year))
        format = request.GET.get('format', 'json')

        facturas_mes = Factura.objects.filter(fecha__month=mes, fecha__year=anio)
        pedidos_mes = Pedidos.objects.filter(fecha_pedido__month=mes, fecha_pedido__year=anio)

        productos_vendidos_pedidos = pedidos_mes.values(
            'producto__nombre',
            'producto__precio'
        ).annotate(
            total_vendido=Sum('cantidad'),
            subtotal=ExpressionWrapper(
                F('producto__precio') * Sum('cantidad'),
                output_field=DecimalField()
            ),
            igv=ExpressionWrapper(
                F('producto__precio') * Sum('cantidad') * 0.18,
                output_field=DecimalField()
            ),
            total=ExpressionWrapper(
                (F('producto__precio') * Sum('cantidad')) - (F('producto__precio') * Sum('cantidad') * 0.18),
                output_field=DecimalField()
            )
        )

        productos_vendidos_facturas = facturas_mes.values(
            'detalles__producto__nombre',
            'detalles__producto__precio'
        ).annotate(
            total_vendido=Sum('detalles__cantidad'),
            subtotal=Sum(F('detalles__cantidad') * F('detalles__producto__precio'), output_field=DecimalField()),
            igv=Sum(F('detalles__cantidad') * F('detalles__producto__precio') * 0.18, output_field=DecimalField()),
            total=Sum(F('detalles__cantidad') * F('detalles__producto__precio') - F('detalles__cantidad') * F('detalles__producto__precio') * 0.18, output_field=DecimalField())
        )

        productos_completos = list(productos_vendidos_pedidos) + list(productos_vendidos_facturas)

        productos_dict = {}
        for producto in productos_completos:
            nombre = producto.get('producto__nombre') or producto.get('detalles__producto__nombre')
            if nombre in productos_dict:
                productos_dict[nombre]['total_vendido'] += producto['total_vendido']
                
                # Redondear los valores a 2 decimales
                productos_dict[nombre]['subtotal'] = round(productos_dict[nombre]['subtotal'] + producto['subtotal'], 2)
                productos_dict[nombre]['igv'] = round(productos_dict[nombre]['igv'] + producto['igv'], 2)
                productos_dict[nombre]['total'] = round(productos_dict[nombre]['total'] + producto['total'], 2)
            else:
                productos_dict[nombre] = {
                    'producto__nombre': nombre,
                    'producto__precio': Decimal(str(producto['producto__precio'])),
                    'total_vendido': producto['total_vendido'],
                    'subtotal': round(Decimal(str(producto['subtotal'])), 2),
                    'igv': round(Decimal(str(producto['igv'])), 2),
                    'total': round(Decimal(str(producto['total'])), 2),
                }

        productos_finales = list(productos_dict.values())

        total_facturado = round(facturas_mes.aggregate(Sum('total'))['total__sum'] or 0, 2)
        total_igv = round(facturas_mes.aggregate(Sum('igv'))['igv__sum'] or 0, 2)
        total_subtotal = round(facturas_mes.aggregate(Sum('subtotal'))['subtotal__sum'] or 0, 2)

        proveedores = pedidos_mes.values(
            'proveedor__nombre'
        ).annotate(
            total_pedidos=Sum('total_pedido')
        )

        total_pedidos = round(pedidos_mes.aggregate(total_pedidos=Sum(F('total_pedido')))['total_pedidos'] or 0, 2)

        reporte = {
            'total_facturado': total_facturado,
            'total_igv': total_igv,
            'total_subtotal': total_subtotal,
            'productos_vendidos': productos_finales,
            'proveedores': [
                {
                    'proveedor__nombre': prov['proveedor__nombre'],
                    'total_pedidos': round(prov['total_pedidos'], 2)
                }
                for prov in proveedores
            ],
            'total_pedidos': total_pedidos,
            'total_pedidos_count': pedidos_mes.count(),
        }

        if format == 'json':
            return JsonResponse(reporte)

        if format == 'pdf':
            template = 'reporte_mensual.html'
            html = render_to_string(template, {'reporte': reporte, 'mes': mes, 'anio': anio})

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="reporte_mensual_{mes}_{anio}.pdf"'
            pisa_status = pisa.CreatePDF(html, dest=response)

            if pisa_status.err:
                return HttpResponse('Error al generar el PDF', status=500)

            return response
