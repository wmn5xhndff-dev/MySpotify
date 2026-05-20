import json
from urllib.parse import quote_plus

import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import ChatMessage, Song
from .music_bot import process_message

DEEZER_TIMEOUT_SECONDS = 10
DEEZER_PAGE_SIZE = 20


def _get_favorite_map(user):
    if not user or not user.is_authenticated:
        return {}
    qs = (Song.objects
          .filter(user=user, is_favorite=True)
          .exclude(deezer_id__isnull=True)
          .exclude(deezer_id=""))
    return {s.deezer_id: s.id for s in qs}


def home(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        url = (
            f"https://api.deezer.com/search"
            f"?q={quote_plus(query)}&limit={DEEZER_PAGE_SIZE}&index=0"
        )
        try:
            response = requests.get(url, timeout=DEEZER_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            results = payload.get("data", [])
        except (requests.RequestException, ValueError):
            results = []

    favorite_map = _get_favorite_map(request.user)
    for track in results:
        track_id = str(track.get("id", ""))
        track["is_favorite"] = track_id in favorite_map
        track["favorite_song_id"] = favorite_map.get(track_id)

    recent_songs = []
    if not query and request.user.is_authenticated:
        recent_songs = list(
            Song.objects.filter(user=request.user, is_favorite=True)
            .order_by("-created_at")[:12]
        )

    return render(request, "music/index.html", {
        "query": query,
        "results": results,
        "has_more": len(results) == DEEZER_PAGE_SIZE,
        "recent_songs": recent_songs,
    })


def search_more(request):
    query = request.GET.get("q", "").strip()
    index = int(request.GET.get("index", DEEZER_PAGE_SIZE))

    if not query:
        return JsonResponse({"tracks": [], "has_more": False})

    url = (
        f"https://api.deezer.com/search"
        f"?q={quote_plus(query)}&limit={DEEZER_PAGE_SIZE}&index={index}"
    )
    try:
        response = requests.get(url, timeout=DEEZER_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        tracks = payload.get("data", [])
    except (requests.RequestException, ValueError):
        return JsonResponse({"tracks": [], "has_more": False})

    favorite_map = _get_favorite_map(request.user)

    result = []
    for t in tracks:
        tid = str(t.get("id", ""))
        result.append({
            "id": tid,
            "title": t.get("title", ""),
            "artist_name": t.get("artist", {}).get("name", ""),
            "cover_medium": t.get("album", {}).get("cover_medium", ""),
            "cover_xl": (
                t.get("album", {}).get("cover_xl")
                or t.get("album", {}).get("cover_big")
                or t.get("album", {}).get("cover_medium", "")
            ),
            "preview": t.get("preview", ""),
            "is_favorite": tid in favorite_map,
            "favorite_song_id": favorite_map.get(tid),
        })

    return JsonResponse({"tracks": result, "has_more": len(tracks) == DEEZER_PAGE_SIZE})


def favorites(request):
    if request.user.is_authenticated:
        songs = Song.objects.filter(user=request.user, is_favorite=True)
    else:
        songs = Song.objects.none()
    return render(request, "music/favorites.html", {"songs": songs})


@require_POST
def add_song(request):
    user = request.user if request.user.is_authenticated else None
    deezer_id = request.POST.get("deezer_id", "").strip()

    defaults = {
        "title": request.POST.get("title", "").strip(),
        "artist": request.POST.get("artist", "").strip(),
        "image_url": request.POST.get("image_url", "").strip() or None,
        "preview_url": request.POST.get("preview_url", "").strip() or None,
        "is_favorite": True,
    }

    if deezer_id and user:
        song, created = Song.objects.get_or_create(
            user=user, deezer_id=deezer_id, defaults=defaults
        )
        if not created and not song.is_favorite:
            song.is_favorite = True
            song.save(update_fields=["is_favorite"])
    elif user:
        Song.objects.create(user=user, **defaults)

    return redirect(request.POST.get("next") or "home")


@require_POST
def toggle_favorite(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    if song.user and song.user != request.user:
        return redirect(request.POST.get("next") or "home")
    song.is_favorite = not song.is_favorite
    song.save(update_fields=["is_favorite"])
    return redirect(request.POST.get("next") or "favorites")


# ── CHAT ──────────────────────────────────────────────────────────────────────

def chat_view(request):
    """Страница чат-бота Music Assistant."""
    user = request.user if request.user.is_authenticated else None

    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()

        if not user_text:
            return JsonResponse({"error": "empty"}, status=400)

        # Очистить историю
        if user_text.lower() in ('очисти историю', 'очистить историю', 'сбрось историю'):
            if user:
                ChatMessage.objects.filter(user=user).delete()
            return JsonResponse({"bot": "История чата очищена! 🗑️", "cleared": True})

        # Сохраняем сообщение пользователя
        ChatMessage.objects.create(user=user, role='user', content=user_text)

        # Получаем ответ бота
        bot_reply = process_message(user_text, user=request.user)

        # Спец-команда очистки из бота
        if bot_reply == '__clear__':
            if user:
                ChatMessage.objects.filter(user=user).delete()
            bot_reply = 'История чата очищена! 🗑️'
            return JsonResponse({"bot": bot_reply, "cleared": True})

        # Сохраняем ответ бота
        ChatMessage.objects.create(user=user, role='bot', content=bot_reply)

        return JsonResponse({"bot": bot_reply})

    # GET — рендерим страницу с историей
    if user:
        history = ChatMessage.objects.filter(user=user).order_by('created_at')[:100]
    else:
        history = []

    return render(request, "music/chat.html", {"history": history})


# ── AUTH ──────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not username:
            messages.error(request, "Введите имя пользователя.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Это имя уже занято.")
        elif len(password1) < 8:
            messages.error(request, "Пароль должен содержать минимум 8 символов.")
        elif password1 != password2:
            messages.error(request, "Пароли не совпадают.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            return redirect("home")

    return render(request, "music/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url or "home")
        else:
            messages.error(request, "Неверный логин или пароль.")
    return render(request, "music/login.html", {"next": request.GET.get("next", "")})


def logout_view(request):
    logout(request)
    return redirect("home")