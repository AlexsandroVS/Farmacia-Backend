from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Sum
from .models import (
    Persona, Empleado, Clientes, Proveedor, 
    Categoria, Producto, Medicamento, Factura,  Pedidos, DetalleFactura
)
from rest_framework.exceptions import ValidationError

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password')
        extra_kwargs = {'password': {'write_only': True}}  
    def create(self, validated_data):
        user = User(**validated_data)  
        user.set_password(validated_data['password']) 
        user.save() 
        return user 

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = '__all__'

class EmpleadoSerializer(serializers.ModelSerializer):
    persona = PersonaSerializer()

    class Meta:
        model = Empleado
        fields = '__all__'

    def create(self, validated_data):
        # Extrae los datos relacionados con Persona
        persona_data = validated_data.pop('persona')
        # Crea una nueva instancia de Persona
        persona_instance = Persona.objects.create(**persona_data)
        # Crea el empleado asociado
        empleado = Empleado.objects.create(persona=persona_instance, **validated_data)
        return empleado

    def update(self, instance, validated_data):
        # Extrae los datos relacionados con Persona
        persona_data = validated_data.pop('persona')
        # Actualiza la instancia de Persona relacionada
        persona_instance = instance.persona  # Obtén la instancia de Persona asociada
        for attr, value in persona_data.items():
            setattr(persona_instance, attr, value)  # Actualiza los campos de Persona
        persona_instance.save()  # Guarda los cambios en Persona

        # Actualiza los campos del empleado
        for attr, value in validated_data.items():
            setattr(instance, attr, value)  # Actualiza los campos del empleado
        instance.save()  # Guarda los cambios en Empleado

        return instance

class ClientesSerializer(serializers.ModelSerializer):
    # Campos del usuario relacionados
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    password = serializers.CharField(write_only=True, required=False)

    # Campos adicionales de Cliente
    direccion = serializers.CharField(required=False)
    dni = serializers.CharField(required=False)

    class Meta:
        model = Clientes
        fields = ['first_name', 'last_name', 'email', 'password', 'direccion', 'dni']

    def validate_dni(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El DNI debe contener solo números.")
        if len(value) != 8:
            raise serializers.ValidationError("El DNI debe tener exactamente 8 dígitos.")
        return value
    def validate_cliente(self, value):
        if not value:
            raise serializers.ValidationError("El cliente es obligatorio.")
        return value

    def create(self, validated_data):
        # Extraer datos del usuario desde validated_data
        user_data = validated_data.pop('user')
        
        # Crear el usuario relacionado
        user = User.objects.create_user(
            username=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            email=user_data['email'],
            password=validated_data.pop('password')
        )
        
        # Crear el cliente asociado con dirección y DNI
        cliente = Clientes.objects.create(user=user, **validated_data)
        return cliente

    def update(self, instance, validated_data):
        # Actualizar campos relacionados con el usuario
        user_data = validated_data.pop('user', {})
        user = instance.user

        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Actualizar campos del cliente
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'
        
class ProveedorTopSerializer(serializers.ModelSerializer):
    total_pedidos = serializers.SerializerMethodField()
    monto_total = serializers.SerializerMethodField()

    class Meta:
        model = Proveedor
        fields = ['id', 'nombre', 'total_pedidos', 'monto_total']

    def get_total_pedidos(self, obj):
        # Asegúrate de que la relación 'pedidos' existe
        return obj.pedidos.count()

    def get_monto_total(self, obj):
        # Calcular la suma total de los pedidos del proveedor
        return obj.pedidos.aggregate(total=Sum('total_pedido'))['total'] or 0.0

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    imagen_url = serializers.SerializerMethodField()  # Campo para la URL completa de la imagen

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 'stock', 'fecha_vencimiento',
            'presentacion', 'categoria', 'categoria_nombre', 'proveedor', 'proveedor_nombre',
            'imagen', 'imagen_url'
        ]

    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and request:
            return request.build_absolute_uri(obj.imagen.url)
        return None

    def validate_fecha_vencimiento(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError("La fecha de vencimiento no puede ser en el pasado.")
        return value
    def update(self, instance, validated_data):
        if 'imagen' in validated_data and not validated_data['imagen']:
            validated_data.pop('imagen')    
        return super().update(instance, validated_data)

class MedicamentoSerializer(serializers.ModelSerializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())

    class Meta:
        model = Medicamento
        fields = '__all__'
 
class DetalleFacturaSerializer(serializers.ModelSerializer):
    producto = serializers.StringRelatedField()  
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleFactura
        fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']
        
class FacturaSerializer(serializers.ModelSerializer):
    detalles = DetalleFacturaSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    igv = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)  # Asegúrate de incluir igv aquí

    class Meta:
        model = Factura
        fields = ['id', 'empleado', 'cliente', 'fecha', 'total', 'subtotal', 'igv', 'detalles']

from rest_framework import serializers
from .models import Pedidos


class PedidosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedidos
        fields = '__all__'

    def validate(self, data):
        """
        Valida y recalcula subtotal, IGV y total_pedido en base a cantidad y precio_compra.
        """
        cantidad = data.get('cantidad', 1)
        precio_compra = float(data.get('precio_compra', 0))
        subtotal = cantidad * precio_compra
        igv = subtotal * 0.18  # Asumiendo una tasa de IGV del 18%
        total_pedido = subtotal + igv

        # Actualiza los valores en los datos validados
        data['subtotal'] = subtotal
        data['igv'] = igv
        data['total_pedido'] = total_pedido
        return data

    def create(self, validated_data):
        """
        Recalcula los valores antes de crear el pedido.
        """
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Recalcula los valores antes de actualizar el pedido.
        """
        return super().update(instance, self.validate(validated_data))

