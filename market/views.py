from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import ServiceOffer, ServiceRequest, TimeTransaction, InteractionRequest, Profile, ChatMessage, Review, Block, Notification, ForumTopic, ForumComment
from .serializers import *
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, F
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()

# Bu durumlar varsa ilan "DOLU" demektir ve listede gözükmemeli
UNAVAILABLE_STATUSES = ['accepted', 'date_proposed', 'scheduled', 'completed']

# --- STANDART CRUD (FİLTRELİ) ---
class ServiceOfferViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Sadece "Müsait" olanları getir
        # Grup offer'lar için (capacity > 1): Sadece tüm spotlar dolduğunda (accepted_count >= capacity) kaldır
        # Normal offer'lar için (capacity = 1): Herhangi bir accepted interaction varsa kaldır
        # Her iki durumda da completed status'ünde olan interaction'ları da kontrol et
        
        # Önce tüm offer'ları al ve accepted_count ekle
        queryset = ServiceOffer.objects.filter(is_visible=True).annotate(
            accepted_count=Count('interactions', filter=Q(interactions__status='accepted'))
        )
        
        # Grup offer'ları (capacity > 1) ve normal offer'ları (capacity = 1) ayrı filtrele
        # Grup offer: accepted_count >= capacity ise veya completed interaction varsa kaldır
        # Normal offer: UNAVAILABLE_STATUSES'de interaction varsa kaldır
        queryset = queryset.exclude(
            Q(capacity__gt=1, accepted_count__gte=F('capacity')) |  # Grup offer: capacity doldu
            Q(capacity__gt=1, interactions__status='completed') |  # Grup offer: completed interaction varsa
            Q(capacity=1, interactions__status__in=UNAVAILABLE_STATUSES)  # Normal offer: UNAVAILABLE_STATUSES'de interaction varsa
        ).distinct().order_by('-created_at')
        
        # Bloklama kontrolü
        if self.request.user.is_authenticated:
            blocked_user_ids = Block.objects.filter(blocker=self.request.user).values_list('blocked_id', flat=True)
            blocking_user_ids = Block.objects.filter(blocked=self.request.user).values_list('blocker_id', flat=True)
            excluded_ids = list(blocked_user_ids) + list(blocking_user_ids)
            queryset = queryset.exclude(user_id__in=excluded_ids)
        
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """Override create to handle is_online logic"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # is_online kontrolü
            is_online = request.data.get('is_online')
            if isinstance(is_online, str):
                is_online = is_online.lower() in ('true', '1', 'on')
            elif isinstance(is_online, bool):
                pass
            else:
                is_online = False
            
            if is_online:
                # Online hizmet: latitude, longitude ve address'i None/boş yap
                serializer.validated_data['latitude'] = None
                serializer.validated_data['longitude'] = None
                serializer.validated_data['address'] = ''  # Boş string kullan (None yerine)
                serializer.validated_data['location'] = '🌐 Online / Remote'
            else:
                # Offline hizmet: Güvenli latitude/longitude dönüşümü
                lat = request.data.get('latitude')
                lon = request.data.get('longitude')
                
                if lat and str(lat).strip():
                    try:
                        serializer.validated_data['latitude'] = float(lat)
                    except (ValueError, TypeError):
                        serializer.validated_data['latitude'] = None
                else:
                    serializer.validated_data['latitude'] = None
                
                if lon and str(lon).strip():
                    try:
                        serializer.validated_data['longitude'] = float(lon)
                    except (ValueError, TypeError):
                        serializer.validated_data['longitude'] = None
                else:
                    serializer.validated_data['longitude'] = None
            
            # is_visible'i zorla True yap
            serializer.validated_data['is_visible'] = True
            
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer): 
        instance = serializer.save(user=self.request.user)
        # is_visible'i zorla True yap (güvenlik için)
        instance.is_visible = True
        instance.save()
    
    def get_object(self):
        # destroy işlemi için kullanıcının kendi ilanlarını getir (is_visible filtresi olmadan)
        if self.request.method == 'DELETE':
            # Superuser ise tüm ilanları görebilir
            if self.request.user.is_superuser:
                queryset = ServiceOffer.objects.all()
            else:
                queryset = ServiceOffer.objects.filter(user=self.request.user)
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(queryset, **filter_kwargs)
            # Superuser için permission check'i atla (destroy metodunda zaten kontrol ediliyor)
            if not self.request.user.is_superuser:
                self.check_object_permissions(self.request, obj)
            return obj
        
        # GET işlemi için: Eğer kullanıcı kendi ilanına bakıyorsa veya ilan görünürse, filtreleri atla
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        
        # Önce normal queryset'ten dene
        try:
            obj = self.get_queryset().get(**filter_kwargs)
            return obj
        except ServiceOffer.DoesNotExist:
            # Eğer normal queryset'te yoksa, kullanıcının kendi ilanı mı kontrol et
            try:
                obj = ServiceOffer.objects.filter(
                    is_visible=True,
                    user=self.request.user
                ).get(**filter_kwargs)
                return obj
            except ServiceOffer.DoesNotExist:
                # Son olarak, interaction üzerinden erişilebilir mi kontrol et
                # (Kullanıcının bir interaction'ı varsa, ilanı görebilir)
                try:
                    obj = ServiceOffer.objects.filter(is_visible=True).get(**filter_kwargs)
                    # Kullanıcının bu ilanla ilgili bir interaction'ı var mı?
                    has_interaction = InteractionRequest.objects.filter(
                        Q(sender=self.request.user) | Q(receiver=self.request.user),
                        offer=obj
                    ).exists()
                    if has_interaction:
                        return obj
                except ServiceOffer.DoesNotExist:
                    pass
                # Hiçbirinde bulunamadı, 404 döndür
                from django.http import Http404
                raise Http404("No ServiceOffer matches the given query.")
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Sadece kendi ilanını silebilir
        if instance.user != request.user:
            return Response({'error': 'You can only delete your own listings'}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Sadece "Müsait" olanları getir
        queryset = ServiceRequest.objects.exclude(
            interactions__status__in=UNAVAILABLE_STATUSES
        ).filter(is_visible=True).distinct().order_by('-created_at')
        
        # Bloklama kontrolü
        if self.request.user.is_authenticated:
            blocked_user_ids = Block.objects.filter(blocker=self.request.user).values_list('blocked_id', flat=True)
            blocking_user_ids = Block.objects.filter(blocked=self.request.user).values_list('blocker_id', flat=True)
            excluded_ids = list(blocked_user_ids) + list(blocking_user_ids)
            queryset = queryset.exclude(user_id__in=excluded_ids)
        
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """Override create to handle is_online logic"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # is_online kontrolü
            is_online = request.data.get('is_online')
            if isinstance(is_online, str):
                is_online = is_online.lower() in ('true', '1', 'on')
            elif isinstance(is_online, bool):
                pass
            else:
                is_online = False
            
            if is_online:
                # Online hizmet: latitude, longitude ve address'i None/boş yap
                serializer.validated_data['latitude'] = None
                serializer.validated_data['longitude'] = None
                serializer.validated_data['address'] = ''  # Boş string kullan (None yerine)
                serializer.validated_data['location'] = '🌐 Online / Remote'
            else:
                # Offline hizmet: Güvenli latitude/longitude dönüşümü
                lat = request.data.get('latitude')
                lon = request.data.get('longitude')
                
                if lat and str(lat).strip():
                    try:
                        serializer.validated_data['latitude'] = float(lat)
                    except (ValueError, TypeError):
                        serializer.validated_data['latitude'] = None
                else:
                    serializer.validated_data['latitude'] = None
                
                if lon and str(lon).strip():
                    try:
                        serializer.validated_data['longitude'] = float(lon)
                    except (ValueError, TypeError):
                        serializer.validated_data['longitude'] = None
                else:
                    serializer.validated_data['longitude'] = None
            
            # is_visible'i zorla True yap
            serializer.validated_data['is_visible'] = True
            
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer): 
        instance = serializer.save(user=self.request.user)
        # is_visible'i zorla True yap (güvenlik için)
        instance.is_visible = True
        instance.save()
    
    def get_object(self):
        # destroy işlemi için kullanıcının kendi ilanlarını getir (is_visible filtresi olmadan)
        if self.request.method == 'DELETE':
            # Superuser ise tüm ilanları görebilir
            if self.request.user.is_superuser:
                queryset = ServiceRequest.objects.all()
            else:
                queryset = ServiceRequest.objects.filter(user=self.request.user)
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(queryset, **filter_kwargs)
            # Superuser için permission check'i atla (destroy metodunda zaten kontrol ediliyor)
            if not self.request.user.is_superuser:
                self.check_object_permissions(self.request, obj)
            return obj
        
        # GET işlemi için: Eğer kullanıcı kendi ilanına bakıyorsa veya ilan görünürse, filtreleri atla
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        
        # Önce normal queryset'ten dene
        try:
            obj = self.get_queryset().get(**filter_kwargs)
            return obj
        except ServiceRequest.DoesNotExist:
            # Eğer normal queryset'te yoksa, kullanıcının kendi ilanı mı kontrol et
            try:
                obj = ServiceRequest.objects.filter(
                    is_visible=True,
                    user=self.request.user
                ).get(**filter_kwargs)
                return obj
            except ServiceRequest.DoesNotExist:
                # Son olarak, interaction üzerinden erişilebilir mi kontrol et
                # (Kullanıcının bir interaction'ı varsa, ilanı görebilir)
                try:
                    obj = ServiceRequest.objects.filter(is_visible=True).get(**filter_kwargs)
                    # Kullanıcının bu ilanla ilgili bir interaction'ı var mı?
                    has_interaction = InteractionRequest.objects.filter(
                        Q(sender=self.request.user) | Q(receiver=self.request.user),
                        service_request=obj
                    ).exists()
                    if has_interaction:
                        return obj
                except ServiceRequest.DoesNotExist:
                    pass
                # Hiçbirinde bulunamadı, 404 döndür
                from django.http import Http404
                raise Http404("No ServiceRequest matches the given query.")
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Sadece kendi ilanını silebilir veya superuser ise
        if instance.user != request.user and not request.user.is_superuser:
            return Response({'error': 'You can only delete your own listings'}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class TimeTransactionViewSet(viewsets.ModelViewSet):
    queryset = TimeTransaction.objects.all()
    serializer_class = TimeTransactionSerializer

    permission_classes = [permissions.IsAuthenticated]

# --- API ---
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_profile_api(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return Response(ProfileSerializer(profile).data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_interactions_api(request):
    """Inbox listesi - Soft delete kontrolü ile + Grup chat'ler"""
    sent = InteractionRequest.objects.filter(
        sender=request.user,
        deleted_by_sender=False
    )
    received = InteractionRequest.objects.filter(
        receiver=request.user,
        deleted_by_receiver=False
    )
    all_interactions = (sent | received).distinct().order_by('-created_at')
    
    # Bloklama kontrolü
    blocked_user_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocking_user_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    excluded_ids = list(blocked_user_ids) + list(blocking_user_ids)
    all_interactions = all_interactions.exclude(
        Q(sender_id__in=excluded_ids) | Q(receiver_id__in=excluded_ids)
    )
    
    # Grup chat'leri ekle: Aynı offer'a sahip accepted interaction'lar için grup chat
    # Kullanıcının accepted interaction'ları olan offer'ları bul
    user_accepted_offers = InteractionRequest.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        status='accepted',
        offer__isnull=False,
        deleted_by_sender=False,
        deleted_by_receiver=False
    ).exclude(
        Q(sender_id__in=excluded_ids) | Q(receiver_id__in=excluded_ids)
    ).values_list('offer_id', flat=True).distinct()
    
    # Her offer için grup chat oluştur (capacity > 1 ise)
    group_chats = []
    for offer_id in user_accepted_offers:
        try:
            offer = ServiceOffer.objects.get(id=offer_id)
            if offer.capacity > 1:
                # Bu offer'a sahip tüm accepted interaction'ları bul
                group_interactions = InteractionRequest.objects.filter(
                    offer_id=offer_id,
                    status='accepted'
                ).exclude(
                    Q(sender_id__in=excluded_ids) | Q(receiver_id__in=excluded_ids)
                )
                
                # Kullanıcının bu grupta olup olmadığını kontrol et
                user_in_group = group_interactions.filter(
                    Q(sender=request.user) | Q(receiver=request.user)
                ).exists()
                
                # İlk kullanıcı kabul edildiğinde bile group chat başlatılmalı
                if user_in_group and group_interactions.count() >= 1:
                    # İlk interaction'ı grup chat olarak kullan (veya özel bir grup chat oluştur)
                    first_interaction = group_interactions.order_by('created_at').first()
                    if first_interaction:
                        # Grup chat'i ekle (sadece bir kez)
                        # Eğer zaten all_interactions'da varsa ekleme, yoksa ekle
                        if not any(i.id == first_interaction.id for i in all_interactions):
                            group_chats.append(first_interaction)
                        # Eğer zaten varsa ama grup chat olarak işaretlenmemişse, işaretle
                        # (Bu durumda zaten result'ta işaretlenecek)
        except ServiceOffer.DoesNotExist:
            continue
    
    # Grup chat'leri ekle
    all_interactions = list(all_interactions) + group_chats
    
    # Serialize et
    result = InteractionRequestSerializer(all_interactions, many=True, context={'request': request}).data
    
    # Grup chat'leri işaretle - TÜM interaction'lar için kontrol et
    for item in result:
        if item.get('offer_id'):
            offer_id = item['offer_id']
            try:
                offer = ServiceOffer.objects.get(id=offer_id)
                # Grup offer ise (capacity > 1) ve accepted status'ünde ise kontrol et
                if offer.capacity > 1 and item.get('status') == 'accepted':
                    # Bu offer'a sahip kaç accepted interaction var?
                    group_count = InteractionRequest.objects.filter(
                        offer_id=offer_id,
                        status='accepted'
                    ).exclude(
                        Q(sender_id__in=excluded_ids) | Q(receiver_id__in=excluded_ids)
                    ).count()
                    # İlk kullanıcı kabul edildiğinde bile group chat başlatılmalı
                    if group_count >= 1:
                        item['is_group_chat'] = True
                        item['group_participants'] = group_count
                    else:
                        item['is_group_chat'] = False
                        item['group_participants'] = 0
                else:
                    item['is_group_chat'] = False
                    item['group_participants'] = 0
            except ServiceOffer.DoesNotExist:
                item['is_group_chat'] = False
                item['group_participants'] = 0
    
    return Response(result)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_listings_api(request):
    """Kullanıcının kendi ilanları (Burada hepsi görünür, statüsü ne olursa olsun)"""
    offers = ServiceOffer.objects.filter(user=request.user).order_by('-created_at')
    reqs = ServiceRequest.objects.filter(user=request.user).order_by('-created_at')
    d1 = ServiceOfferSerializer(offers, many=True, context={'request': request}).data
    d2 = ServiceRequestSerializer(reqs, many=True, context={'request': request}).data
    for i in d1: i['type']='offer'
    for i in d2: i['type']='request'
    return Response(d1+d2)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def pending_requests_api(request):
    """Kullanıcının kendi ilanlarına gelen pending request'ler"""
    # Kullanıcının ilanlarına gelen pending interaction'lar
    pending_interactions = InteractionRequest.objects.filter(
        status='pending',
        receiver=request.user
    ).select_related('sender', 'offer', 'service_request').order_by('-created_at')
    
    # Her pending interaction için listing bilgisi ve sender bilgisi
    result = []
    for interaction in pending_interactions:
        listing = interaction.offer if interaction.offer else interaction.service_request
        if listing:
            result.append({
                'interaction_id': interaction.id,
                'sender_username': interaction.sender.username,
                'sender_id': interaction.sender.id,
                'message': interaction.message,
                'created_at': interaction.created_at,
                'listing_id': listing.id,
                'listing_type': 'offer' if interaction.offer else 'request',
                'listing_title': listing.title,
                'listing_duration': listing.duration,
                'listing_category': listing.category,
            })
    
    return Response(result)

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def interaction_messages_api(request, interaction_id):
    interaction = get_object_or_404(InteractionRequest, id=interaction_id)
    
    # Soft delete kontrolü
    if request.user == interaction.sender and interaction.deleted_by_sender:
        return Response({'error': 'This conversation has been deleted'}, status=status.HTTP_404_NOT_FOUND)
    if request.user == interaction.receiver and interaction.deleted_by_receiver:
        return Response({'error': 'This conversation has been deleted'}, status=status.HTTP_404_NOT_FOUND)
    
    # Grup chat kontrolü: Eğer bu bir grup chat ise (aynı offer'a sahip accepted interaction'lar)
    is_group_chat = False
    if interaction.offer and interaction.offer.capacity > 1 and interaction.status == 'accepted':
        group_interactions = InteractionRequest.objects.filter(
            offer=interaction.offer,
            status='accepted'
        )
        # İlk kullanıcı kabul edildiğinde bile group chat başlatılmalı
        if group_interactions.count() >= 1:
            # Kullanıcının bu grupta olup olmadığını kontrol et
            user_in_group = group_interactions.filter(
                Q(sender=request.user) | Q(receiver=request.user)
            ).exists()
            if user_in_group:
                is_group_chat = True
    
    if not is_group_chat:
        # Normal 1-1 chat kontrolü
        if request.user != interaction.sender and request.user != interaction.receiver:
            return Response({'error': 'Not authorized'}, status=403)

    if request.method == 'GET':
        if is_group_chat:
            # Grup chat: Tüm accepted interaction'ların mesajlarını birleştir
            group_interactions = InteractionRequest.objects.filter(
                offer=interaction.offer,
                status='accepted'
            )
            messages = ChatMessage.objects.filter(interaction__in=group_interactions)
            # Soft delete kontrolü
            messages = messages.exclude(
                Q(deleted_by_sender=True) & Q(interaction__sender=request.user) |
                Q(deleted_by_recipient=True) & Q(interaction__receiver=request.user)
            )
        else:
            # Normal chat: Sadece bu interaction'ın mesajları
            messages = ChatMessage.objects.filter(interaction=interaction)
            if request.user == interaction.sender:
                messages = messages.exclude(deleted_by_sender=True)
            elif request.user == interaction.receiver:
                messages = messages.exclude(deleted_by_recipient=True)
        
        serializer = ChatMessageSerializer(messages.order_by('timestamp'), many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        content = request.data.get('content')
        if not content: return Response({'error': 'No content'}, status=400)
        
        # Grup chat kontrolü
        is_group_chat = False
        if interaction.offer and interaction.offer.capacity > 1 and interaction.status == 'accepted':
            group_interactions = InteractionRequest.objects.filter(
                offer=interaction.offer,
                status='accepted'
            )
            # İlk kullanıcı kabul edildiğinde bile group chat başlatılmalı
            if group_interactions.count() >= 1:
                user_in_group = group_interactions.filter(
                    Q(sender=request.user) | Q(receiver=request.user)
                ).exists()
                if user_in_group:
                    is_group_chat = True
        
        if not is_group_chat:
            # Normal chat: Yetki kontrolü
            if request.user != interaction.sender and request.user != interaction.receiver:
                return Response({'error': 'Not authorized'}, status=403)
        
        # Mesaj oluştur
        msg = ChatMessage.objects.create(interaction=interaction, sender=request.user, content=content)
        
        # Mesaj atılınca etkileşim 'pending' ise ve alıcı yazdıysa kabul et
        if interaction.status == 'pending' and request.user == interaction.receiver:
            interaction.status = 'accepted'
            interaction.save()
            # Bildirim oluştur
            Notification.objects.create(
                user=interaction.sender,
                notification_type='interaction_accepted',
                message=f"{interaction.receiver.username} accepted your interaction request",
                interaction=interaction
            )
        else:
            if is_group_chat:
                # Grup chat: Tüm grup üyelerine bildirim gönder
                group_interactions = InteractionRequest.objects.filter(
                    offer=interaction.offer,
                    status='accepted'
                )
                for group_interaction in group_interactions:
                    other_user = group_interaction.receiver if request.user == group_interaction.sender else group_interaction.sender
                    if other_user != request.user:
                        Notification.objects.create(
                            user=other_user,
                            notification_type='message',
                            message=f"{request.user.username} sent a message in group chat",
                            interaction=group_interaction
                        )
            else:
                # Normal chat: Karşı tarafa bildirim
                other_user = interaction.receiver if request.user == interaction.sender else interaction.sender
                Notification.objects.create(
                    user=other_user,
                    notification_type='message',
                    message=f"{request.user.username} sent you a message",
                    interaction=interaction
                )
        return Response(ChatMessageSerializer(msg).data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def interaction_action_api(request, interaction_id, action):
    # 'delete' action'ı için delete_conversation_api kullanılmalı
    if action == 'delete':
        return Response({'error': 'Use /interaction/<id>/delete/ endpoint'}, status=status.HTTP_400_BAD_REQUEST)
    
    i = get_object_or_404(InteractionRequest, id=interaction_id)
    user = request.user
    if user != i.sender and user != i.receiver: return Response({'error':'Auth'}, 403)

    if action in ['accept', 'decline']:
        if user != i.receiver: return Response({'error':'Unauthorized'},403)
        i.status = 'accepted' if action=='accept' else 'declined'
        i.save()
        if action == 'accept':
            Notification.objects.create(
                user=i.sender,
                notification_type='interaction_accepted',
                message=f"{i.receiver.username} accepted your interaction request",
                interaction=i
            )
            
            # Grup chat kontrolü: Eğer bu bir grup offer ise (capacity > 1), group chat başlat
            # İlk kullanıcı kabul edildiğinde bile group chat başlatılmalı
            if i.offer and i.offer.capacity > 1:
                # Bu offer'a sahip tüm accepted interaction'ları bul (bu yeni kabul edilen dahil)
                all_group_interactions = InteractionRequest.objects.filter(
                    offer=i.offer,
                    status='accepted'
                )
                
                # "joined the group" mesajı kaldırıldı - artık chat başlığında gösterilecek
                # Sadece bildirim gönder
                all_group_interactions = InteractionRequest.objects.filter(
                    offer=i.offer,
                    status='accepted'
                )
                
                # Tüm grup üyelerine bildirim gönder (provider dahil tüm üyelere)
                # Önce tüm unique kullanıcıları bul (tüm interaction'ların sender ve receiver'ları)
                all_group_users = set()
                for group_interaction in all_group_interactions:
                    all_group_users.add(group_interaction.sender)
                    all_group_users.add(group_interaction.receiver)
                
                # Katılan kişi dışındaki tüm üyelere bildirim gönder
                for user in all_group_users:
                    if user != i.receiver:  # Katılan kişiye bildirim gönderme
                        # Her kullanıcı için uygun bir interaction bul (bildirim için)
                        user_interaction = all_group_interactions.filter(
                            Q(sender=user) | Q(receiver=user)
                        ).first()
                        if user_interaction:
                            Notification.objects.create(
                                user=user,
                                notification_type='message',
                                message=f"{i.receiver.username} joined the group chat",
                                interaction=user_interaction
                            )
        return Response({'status': i.status})

    elif action == 'schedule':
        d = request.data.get('date')
        if not d: return Response({'error':'Date?'},400)
        i.appointment_date = d; i.date_proposed_by = user; i.status = 'date_proposed'; i.save()
        # Bildirim oluştur
        other_user = i.receiver if user == i.sender else i.sender
        Notification.objects.create(
            user=other_user,
            notification_type='date_proposed',
            message=f"{user.username} proposed a date: {d}",
            interaction=i
        )
        return Response({'status':'date_proposed'})

    elif action == 'reject_date':
        if i.status != 'date_proposed': return Response({'error':'No date proposed'},400)
        if i.date_proposed_by == user: return Response({'error':'Cannot reject your own date'},400)
        i.status = 'negotiating'
        i.appointment_date = None
        i.date_rejected_by = user
        proposed_by = i.date_proposed_by
        i.date_proposed_by = None
        i.save()
        # Bildirim oluştur
        Notification.objects.create(
            user=proposed_by,
            notification_type='date_rejected',
            message=f"{user.username} rejected your proposed date. Please propose a new date.",
            interaction=i
        )
        return Response({'status':'negotiating'})

    elif action == 'accept_date':
        if i.date_proposed_by == user: return Response({'error':'Wait other party'},400)
        i.status = 'scheduled'; i.save()
        # Bildirim oluştur
        Notification.objects.create(
            user=i.date_proposed_by,
            notification_type='date_accepted',
            message=f"{user.username} accepted your proposed date. Transaction scheduled!",
            interaction=i
        )
        return Response({'status':'scheduled'})

    elif action == 'complete':
        provider = i.receiver if i.offer else i.sender
        if user != provider: return Response({'error':'Only provider can complete'},403)
        i.is_completed_by_provider = True; i.save()
        
        # Grup chat kontrolü
        is_group_chat = False
        if i.offer and i.offer.capacity > 1:
            group_interactions = InteractionRequest.objects.filter(
                offer=i.offer,
                status='accepted'
            )
            if group_interactions.count() > 1:
                is_group_chat = True
        
        if is_group_chat:
            # Grup chat: Tüm grup interaction'larına completion card mesajı gönder
            group_interactions = InteractionRequest.objects.filter(
                offer=i.offer,
                status='accepted'
            )
            
            # Tüm grup interaction'larını is_completed_by_provider = True olarak işaretle
            for group_i in group_interactions:
                group_i.is_completed_by_provider = True
                group_i.save()
            
            # Zaten completion card var mı kontrol et
            existing_card = ChatMessage.objects.filter(
                interaction__in=group_interactions,
                sender=provider
            ).order_by('-timestamp').first()
            
            if existing_card:
                try:
                    card_data = json.loads(existing_card.content)
                    if card_data.get('type') == 'completion_card' and card_data.get('offer_id') == i.offer.id:
                        # Zaten completion card var, tekrar gönderme
                        return Response({'status':'waiting_confirmation', 'message':'Completion card already exists'})
                except:
                    pass
            
            # Tüm katılımcıları topla
            participants = []
            for group_i in group_interactions:
                participant = group_i.sender if group_i.receiver == provider else group_i.receiver
                if participant != provider:
                    participants.append(participant.username)
            
            # Her grup interaction'ına completion card mesajı gönder (sadece bir kez)
            completion_card = {
                'type': 'completion_card',
                'offer_id': i.offer.id,
                'participants': participants,
                'confirmed': []
            }
            
            # Sadece ilk interaction'a mesaj gönder (diğerleri frontend'de birleştirilecek)
            first_interaction = group_interactions.order_by('created_at').first()
            if first_interaction:
                ChatMessage.objects.create(
                    interaction=first_interaction,
                    sender=provider,
                    content=json.dumps(completion_card)
                )
            
            # Tüm katılımcılara bildirim gönder
            for group_i in group_interactions:
                consumer = group_i.sender if group_i.receiver == provider else group_i.receiver
                if consumer != provider:
                    Notification.objects.create(
                        user=consumer,
                        notification_type='completed',
                        message=f"{user.username} marked the group service as completed. Please confirm payment.",
                        interaction=group_i
                    )
        else:
            # Normal 1-1 chat: Karşı tarafa bildirim gönder
            consumer = i.sender if i.offer else i.receiver
            Notification.objects.create(
                user=consumer,
                notification_type='completed',
                message=f"{user.username} marked the transaction as completed. Please confirm to finalize.",
                interaction=i
            )
        
        return Response({'status':'waiting_confirmation'})

    elif action == 'confirm':
        consumer = i.sender if i.offer else i.receiver
        if user != consumer: return Response({'error':'Only consumer can confirm'},403)
        
        # Grup chat kontrolü
        is_group_chat = False
        if i.offer and i.offer.capacity > 1:
            group_interactions = InteractionRequest.objects.filter(
                offer=i.offer,
                status='accepted'
            )
            if group_interactions.count() > 1:
                is_group_chat = True
        
        duration = i.offer.duration if i.offer else i.service_request.duration
        provider = i.receiver if i.offer else i.sender
        
        if is_group_chat:
            # Grup chat: Completion card'ın varlığını kontrol et (provider complete etmiş mi?)
            # Completion card var mı kontrol et
            all_messages = ChatMessage.objects.filter(interaction__in=group_interactions).order_by('-timestamp')
            has_completion_card = False
            for msg in all_messages:
                try:
                    card_data = json.loads(msg.content)
                    if card_data.get('type') == 'completion_card' and card_data.get('offer_id') == i.offer.id:
                        has_completion_card = True
                        break
                except:
                    continue
            
            if not has_completion_card:
                return Response({'error':'Not completed yet'},400)
            
            # Grup chat: Completion card'daki confirmed listesine ekle
            
            # En son completion card mesajını bul ve güncelle
            all_messages = ChatMessage.objects.filter(interaction__in=group_interactions).order_by('-timestamp')
            completion_card_msg = None
            for msg in all_messages:
                try:
                    card_data = json.loads(msg.content)
                    if card_data.get('type') == 'completion_card' and card_data.get('offer_id') == i.offer.id:
                        completion_card_msg = msg
                        break
                except:
                    continue
            
            if completion_card_msg:
                # Completion card'ı güncelle
                card_data = json.loads(completion_card_msg.content)
                confirmed_list = card_data.get('confirmed', [])
                
                # Kullanıcı zaten confirmed listesinde mi kontrol et
                if user.username in confirmed_list:
                    # Zaten confirm etmiş, sadece durumu döndür
                    participants = card_data.get('participants', [])
                    confirmed = card_data.get('confirmed', [])
                    
                    if len(confirmed) >= len(participants):
                        return Response({'status':'completed', 'message':'You already confirmed. All participants confirmed. Transfer completed!'})
                    else:
                        return Response({'status':'waiting_others', 'message':f'You already confirmed. Waiting for {len(participants) - len(confirmed)} more participant(s).'})
                
                # Kullanıcı henüz confirm etmemiş, ekle
                confirmed_list.append(user.username)
                card_data['confirmed'] = confirmed_list
                completion_card_msg.content = json.dumps(card_data)
                completion_card_msg.save()
                
                # Tüm grup interaction'larındaki completion card'ları güncelle
                for group_i in group_interactions:
                    group_messages = ChatMessage.objects.filter(interaction=group_i).order_by('-timestamp')
                    for group_msg in group_messages:
                        try:
                            group_card_data = json.loads(group_msg.content)
                            if group_card_data.get('type') == 'completion_card' and group_card_data.get('offer_id') == i.offer.id:
                                group_card_data['confirmed'] = confirmed_list
                                group_msg.content = json.dumps(group_card_data)
                                group_msg.save()
                                break
                        except:
                            continue
                
                # Tüm katılımcılar confirm etti mi kontrol et
                participants = card_data.get('participants', [])
                confirmed = card_data.get('confirmed', [])
                
                if len(confirmed) >= len(participants):
                    # Tüm katılımcılar confirm etti, her katılımcı için ayrı transfer yap
                    prov_prof, _ = Profile.objects.get_or_create(user=provider)
                    
                    # Her katılımcı duration kadar öder
                    for participant_username in participants:
                        try:
                            participant_user = User.objects.get(username=participant_username)
                            cons_prof, _ = Profile.objects.get_or_create(user=participant_user)
                            
                            # Her katılımcı duration kadar öder
                            cons_prof.balance -= duration
                            cons_prof.save()
                            
                            # Her katılımcı için ayrı transaction kaydı
                            TimeTransaction.objects.create(offer=i.offer, amount=duration)
                        except User.DoesNotExist:
                            continue
                    
                    # Provider sadece duration kadar alır (her katılımcıdan değil, toplam duration kadar)
                    prov_prof.balance += duration
                    prov_prof.save()
                    
                    # Provider toplam duration kadar alır
                    total_duration = duration
                    
                    # Tüm interaction'ları completed yap
                    for group_i in group_interactions:
                        group_i.is_confirmed_by_receiver = True
                        group_i.status = 'completed'
                        group_i.save()
                    
                    # Bildirim gönder
                    Notification.objects.create(
                        user=provider,
                        notification_type='completed',
                        message=f"All participants confirmed payment! You received {total_duration} hours total.",
                        interaction=i
                    )
                    
                    return Response({'status':'completed', 'message':'All participants confirmed. Transfer success!'})
                else:
                    # Henüz tüm katılımcılar confirm etmedi
                    return Response({'status':'waiting_others', 'message':f'You confirmed. Waiting for {len(participants) - len(confirmed)} more participant(s).'})
            else:
                return Response({'error':'Completion card not found'}, 400)
        else:
            # Normal 1-1 chat
            cons_prof, _ = Profile.objects.get_or_create(user=consumer)
            prov_prof, _ = Profile.objects.get_or_create(user=provider)
            
            cons_prof.balance -= duration
            cons_prof.save()
            prov_prof.balance += duration
            prov_prof.save()
            
            TimeTransaction.objects.create(offer=i.offer, request=i.service_request, amount=duration)
            i.is_confirmed_by_receiver = True; i.status = 'completed'; i.save()
            
            # Bildirim oluştur
            Notification.objects.create(
                user=provider,
                notification_type='completed',
                message=f"Transaction completed! You received {duration} hours.",
                interaction=i
            )
            
            return Response({'status':'completed', 'message':'Transfer success'})

    # 'delete' action'ı için delete_conversation_api kullanılmalı
    if action == 'delete':
        return Response({'error': 'Use /interaction/<id>/delete/ endpoint instead of /interaction/<id>/delete/'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'error':'Invalid action'},400)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_interaction_api(request):
    obj_type = request.data.get('type')
    obj_id = request.data.get('id')
    msg = request.data.get('message', '')
    
    if not obj_id or not obj_type: return Response({'error':'Missing data'},400)

    if obj_type == 'offer':
        offer = get_object_or_404(ServiceOffer, id=obj_id)
        if offer.user == request.user: return Response({'error':'Own offer'},400)
        
        # Aynı kullanıcının bu listing'e daha önce request gönderip göndermediğini kontrol et
        existing_interaction = InteractionRequest.objects.filter(
            sender=request.user,
            offer=offer
        ).first()
        
        if existing_interaction:
            return Response({'error': 'You have already contacted this service provider. Check your inbox for the conversation.'}, 400)
        
        # Eğer bu ilan zaten DOLU ise başvurdurma!
        # Grup offer'lar için (capacity > 1): Sadece tüm spotlar dolduğunda (accepted_count >= capacity) DOLU
        # Normal offer'lar için (capacity = 1): Herhangi bir accepted interaction varsa DOLU
        if offer.capacity > 1:
            # Grup offer: accepted_count >= capacity ise DOLU
            accepted_count = InteractionRequest.objects.filter(
                offer=offer, 
                status='accepted'
            ).count()
            if accepted_count >= offer.capacity:
                return Response({'error':'This offer is no longer available.'}, 400)
        else:
            # Normal offer: accepted interaction varsa DOLU
            if InteractionRequest.objects.filter(offer=offer, status__in=UNAVAILABLE_STATUSES).exists():
                return Response({'error':'This offer is no longer available.'}, 400)

        buyer_p, _ = Profile.objects.get_or_create(user=request.user)
        if buyer_p.balance < offer.duration: return Response({'error': f'Insufficient balance!'},400)
        
        ir = InteractionRequest.objects.create(sender=request.user, receiver=offer.user, offer=offer, message=msg)
        Notification.objects.create(
            user=offer.user,
            notification_type='message',
            message=f"{request.user.username} sent you a message about your offer: {offer.title}",
            interaction=ir
        )
        return Response({'success':True, 'id':ir.id})

    elif obj_type == 'request':
        req = get_object_or_404(ServiceRequest, id=obj_id)
        if req.user == request.user: return Response({'error':'Own request'},400)
        
        # Aynı kullanıcının bu listing'e daha önce request gönderip göndermediğini kontrol et
        existing_interaction = InteractionRequest.objects.filter(
            sender=request.user,
            service_request=req
        ).first()
        
        if existing_interaction:
            return Response({'error': 'You have already contacted this service requester. Check your inbox for the conversation.'}, 400)
        
        if InteractionRequest.objects.filter(service_request=req, status__in=UNAVAILABLE_STATUSES).exists():
             return Response({'error':'This request is no longer available.'}, 400)

        ir = InteractionRequest.objects.create(sender=request.user, receiver=req.user, service_request=req, message=msg)
        Notification.objects.create(
            user=req.user,
            notification_type='message',
            message=f"{request.user.username} sent you a message about your request: {req.title}",
            interaction=ir
        )
        return Response({'success':True, 'id':ir.id})

    return Response({'error':'Invalid type'},400)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_count(request): 
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'count': count})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_list_api(request): 
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    return Response([{
        'id': n.id,
        'type': n.notification_type,
        'message': n.message,
        'is_read': n.is_read,
        'created_at': n.created_at,
        'interaction_id': n.interaction.id if n.interaction else None
    } for n in notifications])

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notifications_read_api(request):
    """Tüm okunmamış bildirimleri okundu olarak işaretle"""
    try:
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'success', 'marked_read': updated})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
def register_api(request):
    if request.method != 'POST': return Response({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        if User.objects.filter(username=data.get('username')).exists(): return Response({'error': 'Taken'}, status=400)
        User.objects.create_user(username=data['username'], email=data['email'], password=data['password'])
        return Response({'success': True})
    except Exception as e: return Response({'error': str(e)}, status=400)

def profile_view(request, username):
    """Profil sayfası - Kullanıcının bilgilerini, ilanlarını ve yorumlarını göster"""
    try:
        user = User.objects.get(username=username)
        profile = user.profile
        
        # Aktif ilanlar (sadece bu kullanıcının ilanları, is_visible=True ve UNAVAILABLE_STATUSES'de olmayan interaction'ı olmayanlar)
        active_offers = ServiceOffer.objects.filter(
            user=user, 
            is_visible=True
        ).exclude(
            interactions__status__in=UNAVAILABLE_STATUSES
        ).distinct().order_by('-created_at')
        
        active_requests = ServiceRequest.objects.filter(
            user=user, 
            is_visible=True
        ).exclude(
            interactions__status__in=UNAVAILABLE_STATUSES
        ).distinct().order_by('-created_at')
        
        # Aktif ilanları birleştir
        active_listings = []
        for offer in active_offers:
            active_listings.append({
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'category': offer.category,
                'duration': offer.duration,
                'type': 'offer',
                'created_at': offer.created_at,
                'is_online': offer.is_online,
                'image_url': offer.image.url if offer.image else None,
                'address': offer.address or '',
                'user_username': offer.user.username,
            })
        for req in active_requests:
            active_listings.append({
                'id': req.id,
                'title': req.title,
                'description': req.description,
                'category': req.category,
                'duration': req.duration,
                'type': 'request',
                'created_at': req.created_at,
                'is_online': req.is_online,
                'image_url': req.image.url if req.image else None,
                'address': req.address or '',
                'user_username': req.user.username,
            })
        active_listings.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Tamamlanan hizmetler (sadece bu kullanıcının ilanlarının completed interaction'ları)
        # Kullanıcının oluşturduğu ilanların completed interaction'larını göster
        completed_interactions = InteractionRequest.objects.filter(
            Q(sender=user) | Q(receiver=user),
            status='completed'
        ).select_related('offer', 'service_request', 'sender', 'receiver').order_by('-created_at')
        
        completed_services = []
        seen_listings = set()  # Duplicate'leri önlemek için
        
        for interaction in completed_interactions:
            # Sadece bu kullanıcının oluşturduğu ilanları göster
            if interaction.offer and interaction.offer.user == user:
                listing = interaction.offer
                other_user = interaction.receiver if interaction.sender == user else interaction.sender
                listing_key = f"offer_{listing.id}"
                if listing_key not in seen_listings:
                    seen_listings.add(listing_key)
                    completed_services.append({
                        'id': listing.id,
                        'title': listing.title,
                        'description': listing.description,
                        'category': listing.category,
                        'duration': listing.duration,
                        'type': 'offer',
                        'created_at': listing.created_at,
                        'completed_at': interaction.created_at,
                        'is_online': listing.is_online,
                        'image_url': listing.image.url if listing.image else None,
                        'other_user': other_user.username,
                        'other_user_id': other_user.id,
                    })
            elif interaction.service_request and interaction.service_request.user == user:
                listing = interaction.service_request
                other_user = interaction.receiver if interaction.sender == user else interaction.sender
                listing_key = f"request_{listing.id}"
                if listing_key not in seen_listings:
                    seen_listings.add(listing_key)
                    completed_services.append({
                        'id': listing.id,
                        'title': listing.title,
                        'description': listing.description,
                        'category': listing.category,
                        'duration': listing.duration,
                        'type': 'request',
                        'created_at': listing.created_at,
                        'completed_at': interaction.created_at,
                        'is_online': listing.is_online,
                        'image_url': listing.image.url if listing.image else None,
                        'other_user': other_user.username,
                        'other_user_id': other_user.id,
                    })
        completed_services.sort(key=lambda x: x['completed_at'], reverse=True)
        
        # Kullanıcının aldığı yorumları getir (başkalarından aldığı)
        reviews_received = Review.objects.filter(target_user=user).select_related('reviewer', 'offer', 'service_request').order_by('-created_at')
        
        # Provider ve Consumer reviewlarını ayır
        reviews_as_provider = []
        reviews_as_consumer = []
        
        for review in reviews_received:
            is_provider = False
            if review.offer:
                is_provider = (review.offer.user == user)
            elif review.service_request:
                is_provider = (review.service_request.user != user)
            
            if is_provider:
                reviews_as_provider.append(review)
            else:
                reviews_as_consumer.append(review)
        
        # İstatistikler
        provider_count = len(reviews_as_provider)
        consumer_count = len(reviews_as_consumer)
        provider_avg = sum(r.rating for r in reviews_as_provider) / provider_count if provider_count > 0 else 0
        consumer_avg = sum(r.rating for r in reviews_as_consumer) / consumer_count if consumer_count > 0 else 0
        
        # Kullanıcının verdiği yorumları getir (başkalarına verdiği)
        reviews_given = Review.objects.filter(reviewer=user).select_related('target_user', 'offer', 'service_request').order_by('-created_at')
        
        # Toplam reviews sayısı - sadece alınan reviewlar (provider + consumer)
        total_reviews_count = provider_count + consumer_count
        
        # Ortalama puan hesapla
        average_rating = profile.average_rating
        active_count = len(active_listings)
        completed_count = len(completed_services)
        
        context = {
            'profile_user': user,
            'profile': profile,
            'active_listings': active_listings,
            'completed_services': completed_services,
            'reviews_received': reviews_received,
            'reviews_as_provider': reviews_as_provider,
            'reviews_as_consumer': reviews_as_consumer,
            'provider_count': provider_count,
            'consumer_count': consumer_count,
            'provider_avg': round(provider_avg, 1),
            'consumer_avg': round(consumer_avg, 1),
            'reviews_given': reviews_given,
            'total_reviews_count': total_reviews_count,
            'average_rating': average_rating,
            'active_count': active_count,
            'completed_count': completed_count,
            'is_own_profile': request.user.is_authenticated and request.user == user,
        }
        return render(request, 'market/profile.html', context)
    except User.DoesNotExist:
        from django.http import Http404
        raise Http404("User not found")

# Backward compatibility
def profile_page(request, username):
    return profile_view(request, username)

@api_view(['POST', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def edit_profile_api(request):
    """Kullanıcının profilini güncelle (avatar, bio, location)"""
    try:
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response({'status': 'error', 'message': 'Validation failed', 'errors': serializer.errors}, 
                       status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_review_api(request, username):
    """Yorum yapma - Sadece geçmişte etkileşimi olan kullanıcılar yorum yapabilir"""
    try:
        target_user = User.objects.get(username=username)
        
        # Kendine yorum yapamaz
        if request.user == target_user:
            return Response({'status': 'error', 'message': 'You cannot review yourself'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Geçmişte etkileşim kontrolü
        has_interaction = InteractionRequest.objects.filter(
            Q(sender=request.user, receiver=target_user) | Q(sender=target_user, receiver=request.user),
            status='completed'
        ).exists()
        
        if not has_interaction:
            return Response({'status': 'error', 'message': 'You can only review users you have completed transactions with'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        offer_id = request.data.get('offer_id')
        request_id = request.data.get('request_id')
        
        if not rating or not (1 <= int(rating) <= 5):
            return Response({'status': 'error', 'message': 'Valid rating (1-5) is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Mevcut yorumu kontrol et
        existing_review = None
        if offer_id:
            try:
                offer = ServiceOffer.objects.get(id=offer_id)
                existing_review = Review.objects.filter(reviewer=request.user, offer=offer).first()
            except ServiceOffer.DoesNotExist:
                pass
        elif request_id:
            try:
                req = ServiceRequest.objects.get(id=request_id)
                existing_review = Review.objects.filter(reviewer=request.user, service_request=req).first()
            except ServiceRequest.DoesNotExist:
                pass
        
        if existing_review:
            # Mevcut yorumu güncelle
            existing_review.rating = int(rating)
            existing_review.comment = comment
            existing_review.save()
            serializer = ReviewSerializer(existing_review, context={'request': request})
            return Response({'status': 'success', 'message': 'Review updated', 'review': serializer.data})
        else:
            # Yeni yorum oluştur
            review_data = {
                'reviewer': request.user,
                'target_user': target_user,
                'rating': int(rating),
                'comment': comment,
            }
            if offer_id:
                try:
                    review_data['offer'] = ServiceOffer.objects.get(id=offer_id)
                except ServiceOffer.DoesNotExist:
                    pass
            elif request_id:
                try:
                    review_data['service_request'] = ServiceRequest.objects.get(id=request_id)
                except ServiceRequest.DoesNotExist:
                    pass
            
            review = Review.objects.create(**review_data)
            serializer = ReviewSerializer(review, context={'request': request})
            return Response({'status': 'success', 'message': 'Review created', 'review': serializer.data}, 
                          status=status.HTTP_201_CREATED)
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_by_username_api(request, username):
    """Kullanıcı profilini username ile getir"""
    try:
        user = User.objects.get(username=username)
        profile = user.profile
        serializer = ProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_listings_api(request, username):
    """Kullanıcının ilanlarını getir"""
    try:
        user = User.objects.get(username=username)
        is_own = request.user == user
        
        offers = ServiceOffer.objects.filter(user=user)
        requests = ServiceRequest.objects.filter(user=user)
        
        # Eğer kendi profili değilse sadece görünür olanları getir
        if not is_own:
            offers = offers.filter(is_visible=True)
            requests = requests.filter(is_visible=True)
        
        offers_data = ServiceOfferSerializer(offers, many=True, context={'request': request}).data
        requests_data = ServiceRequestSerializer(requests, many=True, context={'request': request}).data
        
        for item in offers_data:
            item['type'] = 'offer'
        for item in requests_data:
            item['type'] = 'request'
        
        return Response(offers_data + requests_data)
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_history_api(request, username):
    """Kullanıcının tamamlanmış etkileşimlerini getir"""
    try:
        user = User.objects.get(username=username)
        is_own = request.user == user
        
        # Sadece kendi geçmişini görebilir veya show_history=True ise
        if not is_own and not user.profile.show_history:
            return Response({'status': 'error', 'message': 'User history is private'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        interactions = InteractionRequest.objects.filter(
            Q(sender=user) | Q(receiver=user),
            status='completed'
        ).order_by('-created_at')
        
        serializer = InteractionRequestSerializer(interactions, many=True, context={'request': request})
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_reviews_api(request, username):
    """Kullanıcının aldığı yorumları getir"""
    try:
        user = User.objects.get(username=username)
        reviews = Review.objects.filter(target_user=user).order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_review_api(request):
    """Yorum oluştur (genel endpoint)"""
    try:
        target_username = request.data.get('target_username')
        if not target_username:
            return Response({'status': 'error', 'message': 'target_username is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        return add_review_api(request, target_username)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_review_exists_api(request, listing_type, listing_id):
    """Belirli bir ilan için yorum yapılıp yapılmadığını kontrol et"""
    try:
        if listing_type == 'offer':
            listing = ServiceOffer.objects.get(id=listing_id)
            review = Review.objects.filter(reviewer=request.user, offer=listing).first()
        elif listing_type == 'request':
            listing = ServiceRequest.objects.get(id=listing_id)
            review = Review.objects.filter(reviewer=request.user, service_request=listing).first()
        else:
            return Response({'status': 'error', 'message': 'Invalid listing type'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        if review:
            serializer = ReviewSerializer(review, context={'request': request})
            return Response({'exists': True, 'review': serializer.data})
        else:
            return Response({'exists': False})
    except (ServiceOffer.DoesNotExist, ServiceRequest.DoesNotExist):
        return Response({'status': 'error', 'message': 'Listing not found'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def block_user_api(request, username):
    """Kullanıcıyı blokla veya bloktan kaldır"""
    try:
        blocked_user = User.objects.get(username=username)
        if request.user == blocked_user:
            return Response({'status': 'error', 'message': 'You cannot block yourself'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        if request.method == 'POST':
            # Blokla
            block, created = Block.objects.get_or_create(
                blocker=request.user,
                blocked=blocked_user
            )
            if created:
                return Response({'status': 'success', 'message': f'{username} has been blocked'})
            else:
                return Response({'status': 'success', 'message': f'{username} is already blocked'})
        elif request.method == 'DELETE':
            # Bloktan kaldır
            Block.objects.filter(blocker=request.user, blocked=blocked_user).delete()
            return Response({'status': 'success', 'message': f'{username} has been unblocked'})
    except User.DoesNotExist:
        return Response({'status': 'error', 'message': 'User not found'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def blocked_users_api(request):
    """Bloklanan kullanıcıları listele"""
    blocked = Block.objects.filter(blocker=request.user).select_related('blocked')
    blocked_list = [{'username': b.blocked.username, 'blocked_at': b.created_at} for b in blocked]
    return Response(blocked_list)

@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_conversation_api(request, interaction_id):
    """Sohbeti sil (soft delete)"""
    try:
        interaction = InteractionRequest.objects.get(id=interaction_id)
        if request.user != interaction.sender and request.user != interaction.receiver:
            return Response({'status': 'error', 'message': 'Not authorized'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        if request.user == interaction.sender:
            interaction.deleted_by_sender = True
        else:
            interaction.deleted_by_receiver = True
        interaction.save()
        
        return Response({'status': 'success', 'message': 'Conversation deleted'})
    except InteractionRequest.DoesNotExist:
        return Response({'status': 'error', 'message': 'Conversation not found'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def delete_message_api(request, message_id):
    """Mesajı sil (soft delete)"""
    try:
        message = ChatMessage.objects.get(id=message_id)
        if request.user != message.sender:
            return Response({'status': 'error', 'message': 'You can only delete your own messages'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        if message.interaction.sender == request.user:
            message.deleted_by_sender = True
        else:
            message.deleted_by_recipient = True
        message.save()
        
        return Response({'status': 'success', 'message': 'Message deleted'})
    except ChatMessage.DoesNotExist:
        return Response({'status': 'error', 'message': 'Message not found'}, 
                       status=status.HTTP_404_NOT_FOUND)

# Forum API endpoints
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def forum_topics_api(request):
    if request.method == 'GET':
        topics = ForumTopic.objects.all().select_related('author').prefetch_related('comments')
        serializer = ForumTopicSerializer(topics, many=True, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = ForumTopicSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def forum_topic_detail_api(request, topic_id):
    try:
        topic = ForumTopic.objects.get(id=topic_id)
        if request.method == 'GET':
            serializer = ForumTopicSerializer(topic, context={'request': request})
            return Response(serializer.data)
        elif request.method == 'DELETE':
            # Sadece kendi topic'ini silebilir veya superuser ise
            if topic.author != request.user and not request.user.is_superuser:
                return Response({'error': 'You can only delete your own topics'}, status=status.HTTP_403_FORBIDDEN)
            topic.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
    except ForumTopic.DoesNotExist:
        return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def forum_comments_api(request, topic_id):
    try:
        topic = ForumTopic.objects.get(id=topic_id)
    except ForumTopic.DoesNotExist:
        return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        comments = topic.comments.all().select_related('author')
        serializer = ForumCommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = ForumCommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user, topic=topic)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_dashboard_stats_api(request):
    """Admin dashboard statistics endpoint - only accessible to admin users"""
    # Total users
    total_users = User.objects.count()
    
    # New users in last 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    new_users_last_7_days = User.objects.filter(date_joined__gte=seven_days_ago).count()
    
    # Total active listings (offers + requests)
    total_listings = ServiceOffer.objects.filter(is_visible=True).count() + ServiceRequest.objects.filter(is_visible=True).count()
    
    # Total forum topics
    total_forum_topics = ForumTopic.objects.count()
    
    # Recent activity (last 5 actions)
    recent_activity = []
    
    # Recent users (last 5)
    recent_users = User.objects.order_by('-date_joined')[:5]
    for user in recent_users:
        recent_activity.append({
            'type': 'user_joined',
            'message': f'{user.username} joined',
            'timestamp': user.date_joined.isoformat()
        })
    
    # Recent listings (last 5)
    recent_offers = ServiceOffer.objects.filter(is_visible=True).order_by('-created_at')[:5]
    for offer in recent_offers:
        recent_activity.append({
            'type': 'listing_created',
            'message': f'New offer: {offer.title} by {offer.user.username}',
            'timestamp': offer.created_at.isoformat()
        })
    
    # Sort by timestamp and take top 5
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:5]
    
    return Response({
        'total_users': total_users,
        'new_users_last_7_days': new_users_last_7_days,
        'total_listings': total_listings,
        'total_forum_topics': total_forum_topics,
        'recent_activity': recent_activity
    })
