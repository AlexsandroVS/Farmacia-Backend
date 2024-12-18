from django.contrib.auth.models import User  # type: ignore
from django.utils import timezone
from django.db import models, transaction
from django.conf import settings
from decimal import Decimal


def get_default_user():
    user, created = User.objects.get_or_create(
        username='defaultuser',
        email='defaultuser@example.com',
        defaults={'last_login': timezone.now()}  # Set current time as default last_login
    )
    return user.id  # Devuelve solo el ID del usuario en lugar del objeto completo
def get_default_empleado():
    # Assuming you already have an Empleado with ID 1, or create one beforehand
    empleado, created = Empleado.objects.get_or_create(
        persona_id=1,  # Replace with the ID of a default persona if needed
        defaults={
            'cargo': 'default',
            'fecha_contratacion': timezone.now(),
            'salario': 0.00
        }
    )
    return empleado.id

class Persona(models.Model):
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)
    identificacion = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.nombre} {self.apellidos}"

class Empleado(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)  # Relación con el usuario
    cargo = models.CharField(max_length=100)
    fecha_contratacion = models.DateField()
    salario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.persona.nombre

class Clientes(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=get_default_user)
    fecha_registro = models.DateField(default=timezone.now)
    direccion = models.CharField(max_length=200, default="calle 123")  
    dni = models.IntegerField(unique=True, default="00000000")
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Proveedor(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200,)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()

    def __str__(self):
        return self.nombre

class Categoria(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    presentacion = models.CharField(max_length=100)
    fecha_vencimiento = models.DateField()
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    imagen = models.ImageField(max_length=500, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    precio_sin_igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)

    def save(self, *args, **kwargs):
        igv_rate = Decimal('0.18')  
        self.precio = self.precio_sin_igv + (self.precio_sin_igv * igv_rate)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

class Medicamento(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE)
    receta_obligatoria = models.BooleanField(default=False)

    def __str__(self):
        return self.producto.nombre

class Factura(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, default=get_default_empleado)
    fecha = models.DateField()
    cliente = models.CharField(max_length=200, default="Cliente")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        """Sobrescribe el método save para no calcular los totales automáticamente."""
        super(Factura, self).save(*args, **kwargs)  # Guardar sin calcular totales

class DetalleFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=7, decimal_places=2, editable=False)  
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)  

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio  # Tomar el precio del producto
        self.subtotal = self.precio_unitario * self.cantidad  # Calcular el subtotal
        super().save(*args, **kwargs)  # Guardar el detalle

class Pedidos(models.Model):
    ESTADOS = [
        ('Pendiente', 'Pendiente'),
        ('En Proceso', 'En Proceso'),
        ('Completado', 'Completado'),
    ]

    fecha_pedido = models.DateField()
    proveedor = models.ForeignKey('Proveedor', on_delete=models.CASCADE, default=1, related_name='pedidos')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_compra = models.DecimalField(max_digits=7, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    igv = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Campo para IGV
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    estado = models.CharField(max_length=50, choices=ESTADOS)

    IGV_RATE = Decimal('0.18')  # Tasa fija del 18%

    def calcular_subtotal(self):
        return self.cantidad * self.precio_compra

    def calcular_igv(self):
        return self.subtotal * self.IGV_RATE

    def calcular_total(self):
        return self.subtotal + self.igv

    def save(self, *args, **kwargs):

        if self.subtotal is None:
            self.subtotal = self.calcular_subtotal()
        if self.igv is None:
            self.igv = self.calcular_igv()
        if self.total_pedido is None:
            self.total_pedido = self.calcular_total()

        if self.pk:  
            previous = Pedidos.objects.get(pk=self.pk)

            if previous.estado != 'Completado' and self.estado == 'Completado':
                with transaction.atomic():
                    # Incrementar el stock del producto
                    if self.producto:
                        self.producto.stock += self.cantidad
                        self.producto.save()

        super().save(*args, **kwargs)

class FacturaCliente(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # El modelo de usuario de Django
        on_delete=models.CASCADE,
        related_name='facturas_cliente'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"FacturaCliente {self.id} - Cliente: {self.cliente.username}"

class DetalleFacturaCliente(models.Model):
    factura = models.ForeignKey(
        FacturaCliente,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'Producto',
        on_delete=models.CASCADE
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Detalle {self.id} - FacturaCliente {self.factura.id}"