from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class ServiceOffer(models.Model):
    """Represents a service offered by a user (e.g., tutoring, repair, coaching)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    duration = models.FloatField(help_text="Duration in hours.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.user})"


class ServiceRequest(models.Model):
    """Represents a request made by one user for another user's offer."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    offer = models.ForeignKey(ServiceOffer, on_delete=models.CASCADE, related_name='requests', null=True, blank=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    duration = models.FloatField(help_text="Requested duration in hours.")
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Request from {self.user} for {self.offer}"


class TimeTransaction(models.Model):
    offer = models.ForeignKey(ServiceOffer, on_delete=models.CASCADE, null=True, blank=True)
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(help_text="Transfer edilen süre", default=0)
    status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        offer_user = self.offer.user.username if self.offer and self.offer.user else "?"
        request_user = self.request.user.username if self.request and self.request.user else "?"
        return f"Transaction between {offer_user} and {request_user}"

