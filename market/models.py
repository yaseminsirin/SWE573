from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    balance = models.IntegerField(default=3, help_text="User time balance")
    def __str__(self): return f"{self.user} - {self.balance} Hours"

class ServiceOffer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    duration = models.IntegerField(default=1)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitude coordinate")
    address = models.TextField(blank=True, help_text="Address text")
    image = models.ImageField(upload_to='listings/', blank=True, null=True, help_text="Listing image")
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
    address = models.TextField(blank=True, help_text="Address text")
    image = models.ImageField(upload_to='listings/', blank=True, null=True, help_text="Listing image")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class InteractionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('accepted', 'Accepted'), ('date_proposed', 'Date Proposed'),
        ('declined', 'Declined'), ('scheduled', 'Scheduled'), ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
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
    is_completed_by_provider = models.BooleanField(default=False)
    is_confirmed_by_receiver = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class ChatMessage(models.Model):
    interaction = models.ForeignKey(InteractionRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['timestamp']

class TimeTransaction(models.Model):
    offer = models.ForeignKey(ServiceOffer, on_delete=models.CASCADE, null=True)
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, null=True)
    amount = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created: Profile.objects.create(user=instance)
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'): Profile.objects.create(user=instance)
    instance.profile.save()