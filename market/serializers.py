from rest_framework import serializers
from .models import ServiceOffer, ServiceRequest, TimeTransaction, InteractionRequest, Profile, ChatMessage
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Profile
        fields = ['username', 'balance']

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'sender_username', 'content', 'timestamp']
        read_only_fields = ['sender', 'timestamp']

class InteractionRequestSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    receiver_username = serializers.ReadOnlyField(source='receiver.username')
    date_proposed_by_username = serializers.ReadOnlyField(source='date_proposed_by.username')
    
    # Dinamik Alanlar (Offer mı Request mi?)
    title = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = InteractionRequest
        fields = [
            'id', 'sender', 'sender_username', 'receiver', 'receiver_username',
            'title', 'duration', 'type', # Dinamik alanlar
            'message', 'status', 'appointment_date', 'date_proposed_by_username',
            'is_completed_by_provider', 'is_confirmed_by_receiver', 'created_at'
        ]
        read_only_fields = ['status', 'created_at']

    def get_title(self, obj):
        return obj.offer.title if obj.offer else (obj.service_request.title if obj.service_request else "Unknown")

    def get_duration(self, obj):
        return obj.offer.duration if obj.offer else (obj.service_request.duration if obj.service_request else 0)

    def get_type(self, obj):
        return 'offer' if obj.offer else 'request'

class ServiceOfferSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_info = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = ServiceOffer
        fields = ['id','user','user_info','title','description','category','duration','latitude','longitude','address','image','image_url','created_at']
        extra_kwargs = {
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
            'address': {'required': False, 'allow_blank': True},
            'image': {'required': False, 'allow_null': True}
        }
    
    def get_user_info(self, obj): return {"id": obj.user.id, "username": obj.user.username} if obj.user else None
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class ServiceRequestSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_info = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = ['id','user','user_info','title','description','category','duration','latitude','longitude','address','image','image_url','created_at']
        extra_kwargs = {
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
            'address': {'required': False, 'allow_blank': True},
            'image': {'required': False, 'allow_null': True}
        }
    
    def get_user_info(self, obj): return {"id": obj.user.id, "username": obj.user.username} if obj.user else None
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class TimeTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTransaction
        fields = '__all__'