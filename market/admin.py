from django.contrib import admin
from .models import ServiceOffer, ServiceRequest, TimeTransaction


@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'duration', 'created_at')
    search_fields = ('title', 'user__username', 'category')


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'duration', 'created_at')
    search_fields = ('title', 'user__username', 'category')


@admin.register(TimeTransaction)
class TimeTransactionAdmin(admin.ModelAdmin):
    list_display = ('offer', 'request', 'duration', 'status', 'created_at')
    search_fields = ('offer__title', 'request__title')
