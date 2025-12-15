from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin Paneli
    path('admin/', admin.site.urls),

    # Ana Sayfa (Frontend)
    path('', TemplateView.as_view(template_name='timebank.html'), name='home'),

    # Market API'leri (İlanlar, Mesajlar vb.)
    path('api/', include('market.api_urls')),
    
    # Market views (Profile page, etc.)
    path('', include('market.urls')),

    # Accounts API'leri (Login, Register - ARTIK BURADAN ÇALIŞACAK)
    path('api/', include('accounts.urls')),
]

# Media files serving
# Development'ta static() kullan, production'da serve() kullan
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Production'da media dosyalarını serve et
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]