from rest_framework import viewsets, permissions
from .models import ServiceOffer, ServiceRequest, TimeTransaction
from .serializers import (
    ServiceOfferSerializer,
    ServiceRequestSerializer,
    TimeTransactionSerializer
)


# 🔹 Everyone can view offers (for frontend testing)
# Later you can change AllowAny → IsAuthenticated
class ServiceOfferViewSet(viewsets.ModelViewSet):
    queryset = ServiceOffer.objects.all()
    serializer_class = ServiceOfferSerializer
    permission_classes = [permissions.AllowAny]  # TEMP: open for testing


# 🔹 Requests are still authenticated — only logged-in users
class ServiceRequestViewSet(viewsets.ModelViewSet):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


# 🔹 Time transactions are also restricted to logged-in users
class TimeTransactionViewSet(viewsets.ModelViewSet):
    queryset = TimeTransaction.objects.all()
    serializer_class = TimeTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
