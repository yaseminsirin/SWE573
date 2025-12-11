from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import ServiceOffer, ServiceRequest, TimeTransaction, InteractionRequest, Profile, ChatMessage
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
        return ServiceOffer.objects.exclude(
            interactions__status__in=UNAVAILABLE_STATUSES
        ).order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer): 
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Sadece kendi ilanını silebilir
        if instance.user != request.user:
            return Response({'error': 'You can only delete your own listings'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Sadece "Müsait" olanları getir
        return ServiceRequest.objects.exclude(
            interactions__status__in=UNAVAILABLE_STATUSES
        ).order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer): 
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Sadece kendi ilanını silebilir
        if instance.user != request.user:
            return Response({'error': 'You can only delete your own listings'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

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
    """Inbox listesi"""
    sent = InteractionRequest.objects.filter(sender=request.user)
    received = InteractionRequest.objects.filter(receiver=request.user)
    all_interactions = (sent | received).distinct().order_by('-created_at')
    return Response(InteractionRequestSerializer(all_interactions, many=True).data)

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
    if request.user != interaction.sender and request.user != interaction.receiver:
        return Response({'error': 'Not authorized'}, status=403)

    if request.method == 'GET':
        serializer = ChatMessageSerializer(interaction.messages.all(), many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        content = request.data.get('content')
        if not content: return Response({'error': 'No content'}, status=400)
        msg = ChatMessage.objects.create(interaction=interaction, sender=request.user, content=content)
        # Mesaj atılınca etkileşim 'pending' ise ve alıcı yazdıysa kabul et
        if interaction.status == 'pending' and request.user == interaction.receiver:
            interaction.status = 'accepted'
            interaction.save()
        return Response(ChatMessageSerializer(msg).data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def interaction_action_api(request, interaction_id, action):
    i = get_object_or_404(InteractionRequest, id=interaction_id)
    user = request.user
    if user != i.sender and user != i.receiver: return Response({'error':'Auth'}, 403)

    if action in ['accept', 'decline']:
        if user != i.receiver: return Response({'error':'Unauthorized'},403)
        i.status = 'accepted' if action=='accept' else 'declined'
        i.save()
        return Response({'status': i.status})

    elif action == 'schedule':
        d = request.data.get('date')
        if not d: return Response({'error':'Date?'},400)
        i.appointment_date = d; i.date_proposed_by = user; i.status = 'date_proposed'; i.save()
        return Response({'status':'date_proposed'})

    elif action == 'accept_date':
        if i.date_proposed_by == user: return Response({'error':'Wait other party'},400)
        i.status = 'scheduled'; i.save()
        return Response({'status':'scheduled'})

    elif action == 'complete':
        provider = i.receiver if i.offer else i.sender
        if user != provider: return Response({'error':'Only provider can complete'},403)
        i.is_completed_by_provider = True; i.save()
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
        
        return Response({'status':'completed', 'message':'Transfer success'})

    return Response({'error':'Invalid'},400)

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
        
        if InteractionRequest.objects.filter(sender=request.user, offer=offer).exclude(status='declined').exists():
            return Response({'error':'Existing request'},400)
            
        i = InteractionRequest.objects.create(sender=request.user, receiver=offer.user, offer=offer, message=msg)
        return Response({'success':True, 'id':i.id})

    elif obj_type == 'request':
        req_obj = get_object_or_404(ServiceRequest, id=obj_id)
        if req_obj.user == request.user: return Response({'error':'Own request'},400)
        
        # Eğer bu talep zaten DOLU ise başvurdurma!
        if InteractionRequest.objects.filter(service_request=req_obj, status__in=UNAVAILABLE_STATUSES).exists():
             return Response({'error':'This request is no longer available.'}, 400)

        if InteractionRequest.objects.filter(sender=request.user, service_request=req_obj).exclude(status='declined').exists():
            return Response({'error':'Existing offer'},400)
            
        i = InteractionRequest.objects.create(sender=request.user, receiver=req_obj.user, service_request=req_obj, message=msg)
        return Response({'success':True, 'id':i.id})

    return Response({'error':'Invalid type'},400)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_count(request): 
    return Response({'count': InteractionRequest.objects.filter(receiver=request.user, status='pending').count()})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_list_api(request): 
    """Tüm bildirimleri getir (alıcı olarak gelen interaction request'ler)"""
    notifications = InteractionRequest.objects.filter(receiver=request.user).order_by('-created_at')[:50]  # Son 50 bildirim
    serializer = InteractionRequestSerializer(notifications, many=True, context={'request': request})
    return Response({'notifications': serializer.data})

@csrf_exempt
def register_api(request):
    if request.method != 'POST': return Response({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        if User.objects.filter(username=data.get('username')).exists(): return Response({'error': 'Taken'}, status=400)
        User.objects.create_user(username=data['username'], email=data['email'], password=data['password'])
        return Response({'success': True})
    except Exception as e: return Response({'error': str(e)}, status=400)