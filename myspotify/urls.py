from django.contrib import admin
from django.urls import path

from music.views import (
    add_song, chat_view, favorites, home, toggle_favorite, search_more,
    register_view, login_view, logout_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('favorites/', favorites, name='favorites'),
    path('add/', add_song, name='add_song'),
    path('favorite/<int:song_id>/toggle/', toggle_favorite, name='toggle_favorite'),
    path('api/search-more/', search_more, name='search_more'),
    path('chat/', chat_view, name='chat'),
    # Auth
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]