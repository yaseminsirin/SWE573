from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOfferViewSet, ServiceRequestViewSet, TimeTransactionViewSet,
    notification_count, notification_list_api, 
    create_interaction_api, 
    my_profile_api, interaction_messages_api, interaction_action_api, my_interactions_api,
    my_listings_api
)

router = DefaultRouter()
router.register(r'service-offers', ServiceOfferViewSet, basename='service-offer')
router.register(r'service-requests', ServiceRequestViewSet, basename='service-request')
router.register(r'transactions', TimeTransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
    
    # DİKKAT: 'register/' satırını buradan SİLDİK. Artık accounts/urls.py hallediyor.
    
    path('profile/', my_profile_api, name='api-profile'),
    path('interactions/', my_interactions_api, name='api-my-interactions'),
    path('my-listings/', my_listings_api, name='api-my-listings'),
    path('interaction/<int:interaction_id>/messages/', interaction_messages_api, name='api-interaction-messages'),
    path('interaction/<int:interaction_id>/<str:action>/', interaction_action_api, name='api-interaction-action'),
    path('notifications/count/', notification_count, name='api-notification-count'),
    path('notifications/list/', notification_list_api, name='api-notification-list'),
    path('interaction/create/', create_interaction_api, name='api-create-interaction'),
]