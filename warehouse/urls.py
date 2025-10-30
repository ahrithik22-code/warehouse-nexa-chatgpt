from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/planner/', include('planner.urls')),
    path('api/imports/', include('imports.urls')),
    path('api/authz/', include('authz.urls')),
]
