from django.contrib import admin
from .models import Song
# Register your models here.

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'created_at') # Какие колонки видеть в списке
    search_fields = ('title', 'artist')           # По каким полям искать