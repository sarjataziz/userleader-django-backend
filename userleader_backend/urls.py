from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger schema view setup
schema_view = get_schema_view(
    openapi.Info(
        title="Userleader API",
        default_version='v1',
        description="API documentation for Userleader Backend",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License")
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Define the health_check function
def health_check(request):
    return HttpResponse("App is running!")

# Define a home view for the root URL
def home_view(request):
    return HttpResponse("Welcome to Userleader Backend!")

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),  # Root URL
    path('api/v1/', include('userleader_app.urls')),  # Include your app's URLs under 'api/v1/'
    path('docs<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
