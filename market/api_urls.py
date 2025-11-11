# webapp/market/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceOfferViewSet, ServiceRequestViewSet, TimeTransactionViewSet

# Django REST Framework router sistemi ile endpointleri tanımlıyoruz
router = DefaultRouter()
router.register(r'offers', ServiceOfferViewSet, basename='offer')
router.register(r'requests', ServiceRequestViewSet, basename='request')
router.register(r'transactions', TimeTransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),  # /api/offers/ , /api/requests/ , /api/transactions/
]
