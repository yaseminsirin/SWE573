from rest_framework import serializers
from .models import ServiceOffer, ServiceRequest, TimeTransaction, InteractionRequest, Profile, ChatMessage, Review, ForumTopic, ForumComment
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    avatar_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Profile
        fields = ['username', 'email', 'balance', 'bio', 'avatar', 'avatar_url', 'location', 'show_history', 'average_rating', 'review_count']
        extra_kwargs = {
            'avatar': {'required': False, 'allow_null': True},
            'bio': {'required': False, 'allow_blank': True},
            'location': {'required': False, 'allow_blank': True},
        }
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

class ReviewSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)
    target_user_username = serializers.CharField(source='target_user.username', read_only=True)
    service_title = serializers.SerializerMethodField(read_only=True)
    
    # Backward compatibility
    rater_username = serializers.CharField(source='reviewer.username', read_only=True)
    rated_user_username = serializers.CharField(source='target_user.username', read_only=True)
    listing_title = serializers.SerializerMethodField(read_only=True)
    score = serializers.IntegerField(source='rating', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'reviewer', 'reviewer_username', 'target_user', 'target_user_username',
                  'offer', 'service_request', 'service_title', 'rating', 'comment', 'created_at',
                  # Backward compatibility
                  'rater_username', 'rated_user_username', 'listing_title', 'score']
        read_only_fields = ['reviewer', 'created_at']
    
    def get_service_title(self, obj):
        """Service başlığını getir"""
        if obj.offer:
            return obj.offer.title
        elif obj.service_request:
            return obj.service_request.title
        return "Deleted Service"
    
    def get_listing_title(self, obj):
        """Backward compatibility - İlan başlığını getir"""
        return self.get_service_title(obj)

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
    offer_id = serializers.SerializerMethodField()
    request_id = serializers.SerializerMethodField()
    offer_capacity = serializers.SerializerMethodField(read_only=True)
    is_group_chat = serializers.SerializerMethodField(read_only=True)
    group_participants = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InteractionRequest
        fields = [
            'id', 'sender', 'sender_username', 'receiver', 'receiver_username',
            'title', 'duration', 'type', # Dinamik alanlar
            'message', 'status', 'appointment_date', 'date_proposed_by_username',
            'is_completed_by_provider', 'is_confirmed_by_receiver', 'created_at',
            'offer_id', 'request_id', 'offer_capacity', # Listing ID'leri ve capacity
            'is_group_chat', 'group_participants' # Grup chat bilgileri
        ]
        read_only_fields = ['status', 'created_at']

    def get_title(self, obj):
        return obj.offer.title if obj.offer else (obj.service_request.title if obj.service_request else "Unknown")

    def get_duration(self, obj):
        return obj.offer.duration if obj.offer else (obj.service_request.duration if obj.service_request else 0)

    def get_type(self, obj):
        return 'offer' if obj.offer else 'request'
    
    def get_offer_id(self, obj):
        return obj.offer.id if obj.offer else None
    
    def get_request_id(self, obj):
        return obj.service_request.id if obj.service_request else None
    
    def get_offer_capacity(self, obj):
        """Offer capacity bilgisini getir (grup kontrolü için)"""
        return obj.offer.capacity if obj.offer else None
    
    def get_is_group_chat(self, obj):
        """Grup chat olup olmadığını kontrol et"""
        # Serializer context'inden gelen is_group_chat değerini kullan
        if hasattr(obj, '_is_group_chat'):
            return obj._is_group_chat
        # Veya direkt kontrol et
        if obj.offer and obj.offer.capacity > 1 and obj.status == 'accepted':
            from .models import InteractionRequest
            group_count = InteractionRequest.objects.filter(
                offer=obj.offer,
                status='accepted'
            ).count()
            return group_count > 1
        return False
    
    def get_group_participants(self, obj):
        """Grup chat'teki katılımcı sayısını getir"""
        if obj.offer and obj.offer.capacity > 1 and obj.status == 'accepted':
            from .models import InteractionRequest
            return InteractionRequest.objects.filter(
                offer=obj.offer,
                status='accepted'
            ).count()
        return 0

class ServiceOfferSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_info = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    accepted_count = serializers.SerializerMethodField(read_only=True)
    pending_interactions = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = ServiceOffer
        fields = ['id','user','user_info','title','description','category','duration','capacity','accepted_count','pending_interactions','latitude','longitude','address','location','image','image_url','is_visible','is_online','created_at']
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
    
    def get_accepted_count(self, obj):
        """Accepted interaction sayısını hesapla"""
        from .models import InteractionRequest
        return InteractionRequest.objects.filter(
            offer=obj,
            status='accepted'
        ).count()
    
    def get_pending_interactions(self, obj):
        """Pending interaction'ları getir (sadece listing sahibi için)"""
        from .models import InteractionRequest
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.user == request.user:
            pending = InteractionRequest.objects.filter(
                offer=obj,
                status='pending'
            ).select_related('sender').order_by('-created_at')
            return [{
                'id': p.id,
                'sender_username': p.sender.username,
                'message': p.message,
                'created_at': p.created_at
            } for p in pending]
        return []

class ServiceRequestSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_info = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = ['id','user','user_info','title','description','category','duration','latitude','longitude','address','location','image','image_url','is_visible','is_online','created_at']
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

class ForumCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = ForumComment
        fields = ['id', 'topic', 'author', 'author_username', 'content', 'created_at', 'updated_at']
        read_only_fields = ['topic', 'author', 'created_at', 'updated_at']

class ForumTopicSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    comment_count = serializers.SerializerMethodField()
    comments = ForumCommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = ForumTopic
        fields = ['id', 'author', 'author_username', 'title', 'content', 'category', 'created_at', 'updated_at', 'comment_count', 'comments']
        read_only_fields = ['author', 'created_at', 'updated_at']
    
    def get_comment_count(self, obj):
        return obj.comments.count()