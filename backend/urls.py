from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Desgrabador API",
        default_version='v1',
        description="API de Extracción de Subtítulos de YouTube",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

def home(request):
    return HttpResponse("""
    <h1>Desgrabador API</h1>
    <ul>
        <li><a href="/swagger/">Swagger UI</a></li>
        <li><a href="/redoc/">ReDoc</a></li>
        <li><a href="/api/subtitles/health/">Health Check</a></li>
    </ul>
    """)

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/subtitles/', include('subtitles.urls')),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
