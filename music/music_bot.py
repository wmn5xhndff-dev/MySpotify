"""
music_bot.py
Returns dict: {"text": str, "tracks": [...], "suggestions": [...]}
tracks = list of Deezer track dicts (id, title, artist_name, cover, preview)
suggestions = list of quick-reply strings
"""
import re
from urllib.parse import quote_plus

import requests

DEEZER_TIMEOUT = 8
WIKI_TIMEOUT = 6

GREETINGS = {'привет', 'хай', 'здравствуй', 'hello', 'hi', 'йоу', 'ку'}
HELP_KEYWORDS = {'помощь', 'помоги', 'help', 'что умеешь', 'команды'}
BYE_KEYWORDS = {'пока', 'до свидания', 'bye', 'выход', 'бывай'}
THANKS_KEYWORDS = {'спасибо', 'благодарю', 'thanks', 'спс'}

HELP_TEXT = """Я Music Assistant — твой музыкальный помощник.

Что я умею:
- найди трек [название]
- найди исполнителя [имя]
- топ треков [артист]
- кто такой [артист] — биография из Wikipedia
- расскажи о [жанр]
- совет — рекомендация
- сколько у меня избранных
- очисти историю"""

GENRE_INFO = {
    'поп': 'Поп-музыка — популярная музыка с простыми мелодиями и запоминающимися припевами. Главные звезды: Taylor Swift, Ed Sheeran, Ариана Гранде.',
    'рок': 'Рок — гитары, ударные, энергичный звук. От The Beatles до Metallica — десятки поджанров.',
    'хип-хоп': 'Хип-хоп зародился в 70-х в Нью-Йорке. Рэп, диджеинг, брейкданс. Drake, Kendrick Lamar, Eminem.',
    'хипхоп': 'Хип-хоп зародился в 70-х в Нью-Йорке. Рэп, диджеинг, брейкданс. Drake, Kendrick Lamar, Eminem.',
    'джаз': 'Джаз — импровизационный жанр XX века. Miles Davis, John Coltrane, Louis Armstrong.',
    'классика': 'Классическая музыка — от Баха до Шостаковича. Симфонии, концерты, оперы.',
    'электронная': 'Электронная музыка — синтезаторы и компьютеры. House, Techno, EDM. Daft Punk, Avicii, Calvin Harris.',
    'r&b': 'R&B — душевная музыка с элементами соула. The Weeknd, Beyonce, Frank Ocean.',
    'металл': 'Метал — тяжелая гитарная музыка. Iron Maiden, Metallica, Slipknot.',
    'латин': 'Латинская музыка — сальса, реггетон, бачата. Bad Bunny, Maluma, J Balvin.',
}

RECOMMENDATIONS = [
    ("Blinding Lights", "The Weeknd"),
    ("Bohemian Rhapsody", "Queen"),
    ("God's Plan", "Drake"),
    ("Shape of You", "Ed Sheeran"),
    ("Lose Yourself", "Eminem"),
    ("Starboy", "The Weeknd"),
    ("Levitating", "Dua Lipa"),
]

MOOD_QUERIES = {
    'грустн': "sad songs acoustic",
    'счастлив': "happy upbeat pop",
    'злой': "metal aggressive",
    'романтич': "romantic love songs",
    'работа': "lofi focus work",
    'тренировк': "workout gym motivation",
}

_rec_idx = [0]


def _deezer_search(query, limit=5):
    try:
        url = f"https://api.deezer.com/search?q={quote_plus(query)}&limit={limit}"
        r = requests.get(url, timeout=DEEZER_TIMEOUT)
        r.raise_for_status()
        raw = r.json().get('data', [])
        return [_fmt_track(t) for t in raw]
    except Exception:
        return []


def _fmt_track(t):
    return {
        "id": str(t.get("id", "")),
        "title": t.get("title", ""),
        "artist_name": t.get("artist", {}).get("name", ""),
        "cover": (t.get("album", {}).get("cover_medium") or ""),
        "cover_xl": (t.get("album", {}).get("cover_xl") or t.get("album", {}).get("cover_big") or t.get("album", {}).get("cover_medium") or ""),
        "preview": t.get("preview", ""),
    }


def _wiki_summary(query):
    """Получает краткую биографию из Wikipedia (русский, потом английский)."""
    for lang in ('ru', 'en'):
        try:
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(query)}"
            r = requests.get(url, timeout=WIKI_TIMEOUT, headers={"User-Agent": "MySpotify/1.0"})
            if r.status_code == 200:
                data = r.json()
                extract = data.get("extract", "")
                if extract and len(extract) > 80:
                    # Берём первые 2 предложения
                    sentences = extract.split('. ')
                    short = '. '.join(sentences[:2])
                    if not short.endswith('.'):
                        short += '.'
                    return short
        except Exception:
            pass
    return None


def _reply(text, tracks=None, suggestions=None):
    return {
        "text": text,
        "tracks": tracks or [],
        "suggestions": suggestions or [],
    }


def process_message(text: str, user=None) -> dict:
    if not text or not text.strip():
        return _reply("Напиши что-нибудь! Я слушаю.", suggestions=["помощь", "совет", "найди трек"])

    msg = text.strip().lower()

    # 1. Приветствие
    if any(g in msg for g in GREETINGS):
        name = f", {user.username}" if user and user.is_authenticated else ""
        return _reply(
            f"Привет{name}! Я Music Assistant. Чем помочь?",
            suggestions=["помощь", "совет", "найди трек", "топ треков Drake"]
        )

    # 2. До свидания
    if any(b in msg for b in BYE_KEYWORDS):
        return _reply("Пока! Возвращайся за хорошей музыкой.")

    # 3. Спасибо
    if any(t in msg for t in THANKS_KEYWORDS):
        return _reply("Пожалуйста! Рад помочь.", suggestions=["совет", "найди трек"])

    # 4. Помощь
    if any(h in msg for h in HELP_KEYWORDS):
        return _reply(HELP_TEXT, suggestions=["совет", "найди трек Blinding Lights", "кто такой Drake", "расскажи о джаз"])

    # 5. Очистка
    if 'очисти' in msg or 'очистить' in msg or 'сбрось' in msg:
        return _reply("__clear__")

    # 6. Статистика избранных
    if any(w in msg for w in ['избранн', 'сколько треков', 'моих треков', 'моя библиотека']):
        if user and user.is_authenticated:
            count = user.songs.filter(is_favorite=True).count()
            if count == 0:
                return _reply("У тебя пока нет избранных треков.", suggestions=["найди трек", "совет"])
            word = "трек" if count == 1 else "трека" if 2 <= count <= 4 else "треков"
            return _reply(f"У тебя {count} {word} в избранном.", suggestions=["найди трек", "совет"])
        return _reply("Войди в аккаунт, чтобы я мог показать твою библиотеку.")

    # 7. Совет / рекомендация
    if any(w in msg for w in ['совет', 'порекомендуй', 'что послушать', 'посоветуй', 'рекомендация']):
        rec = RECOMMENDATIONS[_rec_idx[0] % len(RECOMMENDATIONS)]
        _rec_idx[0] += 1
        tracks = _deezer_search(f"{rec[0]} {rec[1]}", limit=4)
        return _reply(
            f"Рекомендую: {rec[0]} — {rec[1]}",
            tracks=tracks,
            suggestions=["ещё совет", "найди трек", "топ треков The Weeknd"]
        )

    # 8. Жанр
    for genre, info in GENRE_INFO.items():
        if genre in msg:
            tracks = _deezer_search(genre, limit=4)
            return _reply(
                f"{genre.capitalize()}\n\n{info}",
                tracks=tracks,
                suggestions=[f"топ треков {genre}", "совет", "помощь"]
            )

    # 9. Кто такой / биография
    if re.search(r'кто такой|кто такая|расскажи про|расскажи о|биография', msg):
        query = re.sub(r'кто такой|кто такая|расскажи про|расскажи о|биография', '', msg).strip()
        if not query:
            return _reply("Напиши имя артиста, например: кто такой Drake")
        wiki = _wiki_summary(query)
        tracks = _deezer_search(query, limit=4)
        if wiki:
            return _reply(wiki, tracks=tracks, suggestions=[f"топ треков {query}", "совет"])
        elif tracks:
            return _reply(f"Вот треки артиста {query.title()}:", tracks=tracks, suggestions=["совет"])
        return _reply(f"Не нашел информации о {query}.", suggestions=["помощь"])

    # 10. Топ треков
    if 'топ' in msg or 'лучшие треки' in msg or 'хиты' in msg:
        query = re.sub(r'топ треков|топ|лучшие треки|хиты', '', msg).strip()
        if not query:
            return _reply("Напиши имя артиста: топ треков Eminem", suggestions=["топ треков Drake", "топ треков Eminem"])
        tracks = _deezer_search(f'artist:"{query}"', limit=5) or _deezer_search(query, limit=5)
        return _reply(f"Топ треков {query.title()}:", tracks=tracks, suggestions=["совет", f"кто такой {query}"])

    # 11. Найти исполнителя
    if re.search(r'найди исполнителя|найди артиста|исполнитель', msg):
        query = re.sub(r'найди исполнителя|найди артиста|исполнитель', '', msg).strip()
        if not query:
            return _reply("Напиши имя артиста.")
        tracks = _deezer_search(query, limit=5)
        return _reply(f"Треки артиста {query.title()}:", tracks=tracks, suggestions=[f"кто такой {query}", "совет"])

    # 12. Найти трек
    if re.search(r'найди трек|найди песню|поищи|найди', msg):
        query = re.sub(r'найди трек|найди песню|поищи трек|поищи|найди', '', msg).strip()
        if not query:
            return _reply("Напиши название трека.")
        tracks = _deezer_search(query, limit=5)
        if tracks:
            return _reply(f"Результаты поиска «{query}»:", tracks=tracks, suggestions=["ещё совет", "помощь"])
        return _reply(f"Ничего не нашел по запросу «{query}».", suggestions=["попробуй другой запрос", "помощь"])

    # 13. Настроение
    for mood_key, mood_query in MOOD_QUERIES.items():
        if mood_key in msg:
            tracks = _deezer_search(mood_query, limit=4)
            return _reply("Подобрал треки под настроение:", tracks=tracks, suggestions=["ещё совет", "найди трек"])

    # 14. Что играет
    if 'что играет' in msg or 'что сейчас' in msg:
        return _reply("Нажми на любой трек в поиске — он сразу начнет играть!", suggestions=["найди трек", "совет"])

    # 15. Ещё совет
    if 'ещё' in msg and 'совет' in msg:
        rec = RECOMMENDATIONS[_rec_idx[0] % len(RECOMMENDATIONS)]
        _rec_idx[0] += 1
        tracks = _deezer_search(f"{rec[0]} {rec[1]}", limit=4)
        return _reply(f"Рекомендую: {rec[0]} — {rec[1]}", tracks=tracks, suggestions=["ещё совет", "найди трек"])

    # 16. Fallback — пробуем искать
    if len(msg) > 2:
        tracks = _deezer_search(msg, limit=3)
        if tracks:
            return _reply(f"Вот что нашел по запросу «{text.strip()}»:", tracks=tracks, suggestions=["помощь", "совет"])

    return _reply(
        "Не совсем понял. Попробуй:\n- найди трек [название]\n- найди исполнителя [имя]\n- совет\n- помощь",
        suggestions=["помощь", "совет", "найди трек"]
    )