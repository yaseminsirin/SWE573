# market/urls.py
from django.urls import path
from . import views

app_name = 'market'

urlpatterns = [
    # Browse all offers
    path('offers/', views.browse_offers, name='browse_offers'),
    
    # Offer detail page
    path('offer/<int:id>/', views.offer_detail, name='offer_detail'),
    
    # Create interaction request
    path('offer/<int:offer_id>/request/', views.create_interaction_request, name='create_interaction_request'),
    
    # Notifications page
    path('notifications/', views.notifications, name='notifications'),
    
    # Accept/Decline interaction requests
    path('interaction/<int:id>/accept/', views.accept_interaction, name='accept_interaction'),
    path('interaction/<int:id>/decline/', views.decline_interaction, name='decline_interaction'),
    
    # API endpoints
    path('api/notifications/count/', views.notification_count, name='notification_count'),
    path('api/notifications/list/', views.notification_list_api, name='notification_list_api'),
    path('api/offer/<int:offer_id>/request/', views.create_interaction_request_api, name='create_interaction_request_api'),
]

