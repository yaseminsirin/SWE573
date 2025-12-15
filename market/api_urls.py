from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceOfferViewSet, ServiceRequestViewSet, TimeTransactionViewSet,
    notification_count, notification_list_api, mark_notifications_read_api,
    create_interaction_api, 
    my_profile_api, interaction_messages_api, interaction_action_api, my_interactions_api,
    my_listings_api, profile_by_username_api, user_listings_api, user_history_api,
    user_reviews_api, create_review_api, check_review_exists_api, edit_profile_api, add_review_api,
    block_user_api, blocked_users_api, delete_conversation_api, delete_message_api,
    forum_topics_api, forum_topic_detail_api, forum_comments_api, pending_requests_api,
    admin_dashboard_stats_api
)

router = DefaultRouter()
router.register(r'service-offers', ServiceOfferViewSet, basename='service-offer')
router.register(r'service-requests', ServiceRequestViewSet, basename='service-request')
router.register(r'transactions', TimeTransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
    
    # DİKKAT: 'register/' satırını buradan SİLDİK. Artık accounts/urls.py hallediyor.
    
    path('profile/', my_profile_api, name='api-profile'),
    path('profile/edit/', edit_profile_api, name='api-edit-profile'),
    path('profile/<str:username>/', profile_by_username_api, name='api-profile-by-username'),
    path('profile/<str:username>/listings/', user_listings_api, name='api-user-listings'),
    path('profile/<str:username>/history/', user_history_api, name='api-user-history'),
    path('profile/<str:username>/reviews/', user_reviews_api, name='api-user-reviews'),
    path('profile/<str:username>/add-review/', add_review_api, name='api-add-review'),
    path('review/create/', create_review_api, name='api-create-review'),
    path('review/check/<str:listing_type>/<int:listing_id>/', check_review_exists_api, name='api-check-review'),
    path('interactions/', my_interactions_api, name='api-my-interactions'),
    path('my-listings/', my_listings_api, name='api-my-listings'),
    path('pending-requests/', pending_requests_api, name='api-pending-requests'),
    path('interaction/<int:interaction_id>/messages/', interaction_messages_api, name='api-interaction-messages'),
    path('interaction/<int:interaction_id>/delete/', delete_conversation_api, name='api-delete-conversation'),
    path('interaction/<int:interaction_id>/<str:action>/', interaction_action_api, name='api-interaction-action'),
    path('notifications/count/', notification_count, name='api-notification-count'),
    path('notifications/list/', notification_list_api, name='api-notification-list'),
    path('notifications/mark-read/', mark_notifications_read_api, name='api-mark-notifications-read'),
    path('interaction/create/', create_interaction_api, name='api-create-interaction'),
    path('block/<str:username>/', block_user_api, name='api-block-user'),
    path('blocked-users/', blocked_users_api, name='api-blocked-users'),
    path('message/<int:message_id>/delete/', delete_message_api, name='api-delete-message'),
    path('forum-topics/', forum_topics_api, name='api-forum-topics'),
    path('forum-topics/<int:topic_id>/', forum_topic_detail_api, name='api-forum-topic-detail'),
    path('forum-topics/<int:topic_id>/comments/', forum_comments_api, name='api-forum-comments'),
    path('admin/dashboard-stats/', admin_dashboard_stats_api, name='api-admin-dashboard-stats'),
]