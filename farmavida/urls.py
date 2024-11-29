from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView  # Importa TokenVerifyView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from api.views import landing_page

# Configuración de Swagger para la documentación de la API
schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="API for my project",
    ),
    public=True,
)

urlpatterns = [
    path('', landing_page, name='landing_page'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Incluye las URLs de la aplicación 'api'
    path('api-auth/', include('rest_framework.urls')),  # Rutas de autenticación de DRF
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Token JWT
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh JWT
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),  # Ruta para verificar el token
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  # Swagger
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    
