from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import ServiceOffer, ServiceRequest, TimeTransaction, InteractionRequest, Profile, ChatMessage, Review, Block, Notification
from .serializers import *
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json

User = get_user_model()

# Bu durumlar varsa ilan "DOLU" demektir ve listede gözükmemeli
UNAVAILABLE_STATUSES = ['accepted', 'date_proposed', 'scheduled', 'completed']

# --- STANDART CRUD (FİLTRELİ) ---
class ServiceOfferViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Sadece "Müsait" olanları getir (İlişkili interaction'ı "dolu" olmayanlar)
        queryset = ServiceOffer.objects.exclude(
            interactions__status__in=UNAVAILABLE_STATUSES
        ).filter(is_visible=True).order_by('-created_at')
        
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
            queryset = ServiceOffer.objects.filter(user=self.request.user)
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(queryset, **filter_kwargs)
            self.check_object_permissions(self.request, obj)
            return obj
        return super().get_object()
    
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
        ).filter(is_visible=True).order_by('-created_at')
        
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
            queryset = ServiceRequest.objects.filter(user=self.request.user)
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(queryset, **filter_kwargs)
            self.check_object_permissions(self.request, obj)
            return obj
        return super().get_object()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Sadece kendi ilanını silebilir
        if instance.user != request.user:
            return Response({'error': 'You can only delete your own listings'}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
        # Sadece kendi ilanını silebilir
        if instance.user != request.user:
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
    """Inbox listesi - Soft delete kontrolü ile"""
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
    
    return Response(InteractionRequestSerializer(all_interactions, many=True, context={'request': request}).data)

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

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def interaction_messages_api(request, interaction_id):
    interaction = get_object_or_404(InteractionRequest, id=interaction_id)
    
    # Soft delete kontrolü
    if request.user == interaction.sender and interaction.deleted_by_sender:
        return Response({'error': 'This conversation has been deleted'}, status=status.HTTP_404_NOT_FOUND)
    if request.user == interaction.receiver and interaction.deleted_by_receiver:
        return Response({'error': 'This conversation has been deleted'}, status=status.HTTP_404_NOT_FOUND)
    if request.user != interaction.sender and request.user != interaction.receiver:
        return Response({'error': 'Not authorized'}, status=403)

    if request.method == 'GET':
        # Soft delete kontrolü ile mesajları getir
        messages = ChatMessage.objects.filter(interaction=interaction)
        if request.user == interaction.sender:
            messages = messages.exclude(deleted_by_sender=True)
        elif request.user == interaction.receiver:
            messages = messages.exclude(deleted_by_recipient=True)
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        content = request.data.get('content')
        if not content: return Response({'error': 'No content'}, status=400)
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
            # Yeni mesaj bildirimi
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
        
        # Bildirim oluştur - karşı tarafa (consumer'a) bildirim gönder
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
        if not i.is_completed_by_provider: return Response({'error':'Not completed yet'},400)
        
        duration = i.offer.duration if i.offer else i.service_request.duration
        provider = i.receiver if i.offer else i.sender
        
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
        
        # Eğer bu ilan zaten DOLU ise (accepted/scheduled/completed) başvurdurma!
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
        
        # Kullanıcının ilanlarını getir (hem offer hem request)
        offers = ServiceOffer.objects.filter(user=user, is_visible=True).order_by('-created_at')
        requests = ServiceRequest.objects.filter(user=user, is_visible=True).order_by('-created_at')
        
        # Tüm ilanları birleştir
        all_listings = []
        for offer in offers:
            all_listings.append({
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'category': offer.category,
                'duration': offer.duration,
                'type': 'offer',
                'created_at': offer.created_at,
                'is_online': offer.is_online,
                'image_url': offer.image.url if offer.image else None,
            })
        for req in requests:
            all_listings.append({
                'id': req.id,
                'title': req.title,
                'description': req.description,
                'category': req.category,
                'duration': req.duration,
                'type': 'request',
                'created_at': req.created_at,
                'is_online': req.is_online,
                'image_url': req.image.url if req.image else None,
            })
        # En yeni ilanlar önce gelsin
        all_listings.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Kullanıcının aldığı yorumları getir
        all_reviews = Review.objects.filter(target_user=user).order_by('-created_at')
        
        # Yorumları Provider ve Receiver olarak ayır
        reviews_as_provider = []
        reviews_as_receiver = []
        
        for review in all_reviews:
            is_provider = False
            
            # Eğer Review bir ServiceOffer'a bağlıysa
            if review.offer:
                # Kullanıcı offer'ın sahibiyse -> Provider
                if review.offer.user == user:
                    is_provider = True
            
            # Eğer Review bir ServiceRequest'e bağlıysa
            elif review.service_request:
                # Kullanıcı request'in sahibiyse -> Receiver
                if review.service_request.user == user:
                    is_provider = False
                else:
                    # Kullanıcı request'i karşılayan kişiyse -> Provider
                    is_provider = True
            
            if is_provider:
                reviews_as_provider.append(review)
            else:
                reviews_as_receiver.append(review)
        
        # Ortalama puanları hesapla
        # Genel ortalama (tüm yorumlar)
        avg_rating_overall = profile.average_rating if all_reviews.exists() else 0.0
        
        # Provider olarak aldığı yorumların ortalaması
        if reviews_as_provider:
            avg_rating_provider = sum(r.rating for r in reviews_as_provider) / len(reviews_as_provider)
        else:
            avg_rating_provider = 0.0
        
        # Receiver olarak aldığı yorumların ortalaması
        if reviews_as_receiver:
            avg_rating_receiver = sum(r.rating for r in reviews_as_receiver) / len(reviews_as_receiver)
        else:
            avg_rating_receiver = 0.0
        
        listing_count = len(all_listings)
        provider_count = len(reviews_as_provider)
        receiver_count = len(reviews_as_receiver)
        
        context = {
            'profile_user': user,
            'profile': profile,
            'listings': all_listings,
            'reviews': all_reviews,  # Backward compatibility
            'reviews_as_provider': reviews_as_provider,
            'reviews_as_receiver': reviews_as_receiver,
            'provider_count': provider_count,
            'receiver_count': receiver_count,
            'average_rating': avg_rating_overall,  # Backward compatibility
            'avg_rating_overall': avg_rating_overall,
            'avg_rating_provider': avg_rating_provider,
            'avg_rating_receiver': avg_rating_receiver,
            'listing_count': listing_count,
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
