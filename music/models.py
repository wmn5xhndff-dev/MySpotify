from django.contrib.auth.models import User
from django.db import models


class Song(models.Model):
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='songs',
        verbose_name='Пользователь',
    )
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    deezer_id = models.CharField(max_length=50, null=True, blank=True)
    preview_url = models.URLField(max_length=500, null=True, blank=True)
    is_favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [('user', 'deezer_id')]

    def __str__(self):
        return f"{self.artist} — {self.title}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'user'), ('bot', 'bot')]

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='Пользователь',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
