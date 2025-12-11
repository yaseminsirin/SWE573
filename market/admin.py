from django.contrib import admin
from .models import ServiceOffer, ServiceRequest, TimeTransaction, InteractionRequest, Profile, ChatMessage

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

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
    # DÜZELTME: Eski 'duration' ve 'status' alanlarını kaldırdık, 'amount' ekledik
    list_display = ('offer', 'request', 'amount', 'created_at')
    list_filter = ('created_at',)

@admin.register(InteractionRequest)
class InteractionRequestAdmin(admin.ModelAdmin):
    # Yeni eklediğimiz randevu tarihi ve onay durumlarını da gösterelim
    list_display = ('sender', 'receiver', 'offer', 'status', 'appointment_date', 'is_completed_by_provider', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'offer__title')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'interaction', 'short_content', 'timestamp')
    
    def short_content(self, obj):
        return obj.content[:50]