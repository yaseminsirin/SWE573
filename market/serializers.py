from rest_framework import serializers
from .models import ServiceOffer, ServiceRequest, TimeTransaction

# --- USER PUBLIC ---
class UserPublicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


# --- OFFER ---
class ServiceOfferSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ServiceOffer
        fields = [
            'id',
            'user',
            'user_info',
            'title',
            'description',
            'category',
            'duration',
            'created_at',
        ]

    def get_user_info(self, obj):
        """Frontend'de username veya ID göstermek için"""
        return {"id": obj.user.id, "username": obj.user.username} if obj.user else None


# --- REQUEST ---
class ServiceRequestSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_info = serializers.SerializerMethodField(read_only=True)
    offer_title = serializers.ReadOnlyField(source='offer.title', default=None)

    class Meta:
        model = ServiceRequest
        fields = [
            'id',
            'user',
            'user_info',
            'offer',
            'offer_title',
            'title',
            'description',
            'category',
            'duration',
            'created_at',
            'is_approved',
        ]

    def get_user_info(self, obj):
        """İstek atan kullanıcının bilgileri"""
        return {"id": obj.user.id, "username": obj.user.username} if obj.user else None


# --- TRANSACTION ---
class TimeTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTransaction
        fields = '__all__'
