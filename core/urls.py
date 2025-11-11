# webapp/core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # 🌐 Admin paneli
    path('admin/', admin.site.urls),

    # 🏠 Frontend (Ana HTML sayfası)
    path('', TemplateView.as_view(template_name='timebank.html'), name='home'),

    # 🔐 JWT Authentication endpoints
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 👤 Accounts API (örneğin kullanıcı giriş/kayıt işlemleri)
    path('api/accounts/', include('accounts.urls')),

    # 🧩 Market API (offers, requests, transactions)
    path('api/', include('market.api_urls')),
]
