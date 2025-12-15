from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    balance = models.IntegerField(default=3, help_text="User time balance")
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True, help_text="User location")
    show_history = models.BooleanField(default=True)
    
    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        reviews = Review.objects.filter(target_user=self.user)
        if reviews.count() == 0:
            return 0.0
        return reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0.0
    
    @property
    def review_count(self):
        """Get total number of reviews"""
        return Review.objects.filter(target_user=self.user).count()
    
    def get_average_rating(self):
        """Get average rating as a method (for template compatibility)"""
        return self.average_rating
    
    def __str__(self): return f"{self.user} - {self.balance} Hours"

class ServiceOffer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    duration = models.IntegerField(default=1)
    capacity = models.IntegerField(default=1, help_text="Number of spots available for this offer")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitude coordinate")
    address = models.TextField(blank=True, null=True, help_text="Address text")
    location = models.CharField(max_length=200, blank=True, null=True, help_text="Location name (city, district, etc.)")
    image = models.ImageField(upload_to='listings/', blank=True, null=True, help_text="Listing image")
    is_visible = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class ServiceRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    duration = models.IntegerField(default=1)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitude coordinate")
    address = models.TextField(blank=True, null=True, help_text="Address text")
    location = models.CharField(max_length=200, blank=True, null=True, help_text="Location name (city, district, etc.)")
    image = models.ImageField(upload_to='listings/', blank=True, null=True, help_text="Listing image")
    is_visible = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class InteractionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('accepted', 'Accepted'), ('date_proposed', 'Date Proposed'),
        ('declined', 'Declined'), ('scheduled', 'Scheduled'), ('completed', 'Completed'),
        ('cancelled', 'Cancelled'), ('negotiating', 'Negotiating'),
    ]
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_interactions')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_interactions')
    
    # ARTIK HEM OFFER HEM REQUEST OLABİLİR (Biri dolu, diğeri boş olacak)
    offer = models.ForeignKey(ServiceOffer, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    appointment_date = models.DateTimeField(null=True, blank=True)
    date_proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='proposed_dates')
    date_rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_dates')
    is_completed_by_provider = models.BooleanField(default=False)
    is_confirmed_by_receiver = models.BooleanField(default=False)
    deleted_by_sender = models.BooleanField(default=False)
    deleted_by_receiver = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class ChatMessage(models.Model):
    interaction = models.ForeignKey(InteractionRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    deleted_by_sender = models.BooleanField(default=False)
    deleted_by_recipient = models.BooleanField(default=False)
    class Meta: ordering = ['timestamp']

class TimeTransaction(models.Model):
    offer = models.ForeignKey(ServiceOffer, on_delete=models.CASCADE, null=True)
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, null=True)
    amount = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given', null=True, blank=True, help_text="User who wrote the review")
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received', null=True, blank=True, help_text="User being reviewed")
    # Service reference - can be either offer or request
    offer = models.ForeignKey('ServiceOffer', on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    service_request = models.ForeignKey('ServiceRequest', on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5, help_text="Rating from 1 to 5")
    comment = models.TextField(blank=True, help_text="Review comment")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Backward compatibility fields (for existing code)
    @property
    def rater(self):
        return self.reviewer
    
    @property
    def rated_user(self):
        return self.target_user
    
    @property
    def score(self):
        return self.rating
    
    @property
    def listing_type(self):
        if self.offer:
            return 'offer'
        elif self.service_request:
            return 'request'
        return None
    
    @property
    def listing_id(self):
        if self.offer:
            return self.offer.id
        elif self.service_request:
            return self.service_request.id
        return None
    
    class Meta:
        ordering = ['-created_at']
        # Prevent duplicate reviews for the same service
        constraints = [
            models.UniqueConstraint(fields=['reviewer', 'offer'], condition=models.Q(offer__isnull=False), name='unique_offer_review'),
            models.UniqueConstraint(fields=['reviewer', 'service_request'], condition=models.Q(service_request__isnull=False), name='unique_request_review'),
        ]
    
    def __str__(self):
        return f"{self.reviewer.username} rated {self.target_user.username}: {self.rating}/5"

class Block(models.Model):
    """Kullanıcı bloklama sistemi"""
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by_users')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['blocker', 'blocked']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

class Notification(models.Model):
    """Bildirim sistemi"""
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('date_proposed', 'Date Proposed'),
        ('date_rejected', 'Date Rejected'),
        ('date_accepted', 'Date Accepted'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('interaction_accepted', 'Interaction Accepted'),
        ('interaction_declined', 'Interaction Declined'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    interaction = models.ForeignKey(InteractionRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"

class ForumTopic(models.Model):
    """Forum topic modeli"""
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('group_request', 'Group Request'),
        ('event', 'Event'),
        ('help', 'Help'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_topics')
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def comment_count(self):
        return self.comments.count()

class ForumComment(models.Model):
    """Forum comment modeli"""
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.topic.title}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created: Profile.objects.create(user=instance)
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'): Profile.objects.create(user=instance)
    instance.profile.save()