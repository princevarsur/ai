from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls', namespace='accounts')),
    path('api/policies/', include('policies.urls', namespace='policies')),
    path('api/laws/', include('laws.urls', namespace='laws')),
    path('api/compliance/', include('compliance.urls', namespace='compliance')),
    path('api/reports/', include('reports.urls', namespace='reports')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
