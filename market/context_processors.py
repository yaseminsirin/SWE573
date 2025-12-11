# market/context_processors.py
from .models import InteractionRequest


def notification_count(request):
    """Add notification count to template context."""
    if request.user.is_authenticated:
        count = InteractionRequest.objects.filter(
            receiver=request.user,
            status='pending'
        ).count()
        return {'notification_count': count}
    return {'notification_count': 0}

