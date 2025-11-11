from rest_framework import viewsets, permissions
from .models import ServiceOffer, ServiceRequest, TimeTransaction
from .serializers import (
    ServiceOfferSerializer,
    ServiceRequestSerializer,
    TimeTransactionSerializer
)


# 🔹 Service Offers: Require authentication, filter by user, and set user on create
class ServiceOfferViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter offers by the logged-in user
        return ServiceOffer.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the user to the logged-in user
        serializer.save(user=self.request.user)


# 🔹 Service Requests: Require authentication, filter by user, and set user on create
class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter requests by the logged-in user
        return ServiceRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the user to the logged-in user
        serializer.save(user=self.request.user)


# 🔹 Time Transactions: Require authentication, but allow all objects
class TimeTransactionViewSet(viewsets.ModelViewSet):
    queryset = TimeTransaction.objects.all()
    serializer_class = TimeTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
