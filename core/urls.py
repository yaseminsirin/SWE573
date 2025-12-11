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

    # Accounts API'leri (Login, Register - ARTIK BURADAN ÇALIŞACAK)
    path('api/', include('accounts.urls')),
]

# Media files serving (sadece DEBUG=True iken)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)