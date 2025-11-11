from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    balance = models.FloatField(default=0.0, help_text="Kullanıcının toplam zaman bakiyesi (saat cinsinden).")

    # profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    # bio = models.TextField(blank=True)

    def __str__(self):
        return self.username
