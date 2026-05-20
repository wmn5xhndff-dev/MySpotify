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
LASTFM_TIMEOUT = 6
LASTFM_API_KEY = '953df161bc52776025237474a9bd9b45'
LASTFM_BASE = 'http://ws.audioscrobbler.com/2.0/'

GREETINGS = {'привет', 'хай', 'здравствуй', 'hello', 'hi', 'йоу', 'ку'}
HELP_KEYWORDS = {'помощь', 'помоги', 'help', 'что умеешь', 'команды'}
BYE_KEYWORDS = {'пока', 'до свидания', 'bye', 'выход', 'бывай'}
THANKS_KEYWORDS = {'спасибо', 'благодарю', 'thanks', 'спс'}

HELP_TEXT = """Я Music Assistant — твой музыкальный помощник.

Что я умею:
- найди трек [название]
- найди исполнителя [имя]
- топ треков [артист]
- кто такой [артист] — биография
- расскажи о [жанр]
- настроение — подбор музыки по настроению
- совет — recommendation
- сколько у меня избранных
- очисти историю (clear)"""

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
    ("Harvey", "Her's"),
    ("цветы", "тёмный принц"),
    ("Apple Cider", "beabadoobee"),
    ("sad amber perfume", "королевский XVII"),
    ("Babydoll", "Dominic Fike"),
    ("больше, чем творчество", "CUPSIZE"),
]

# Двухэтапное настроение: ключ = текст кнопки (lowercase), значение = поисковый запрос в Deezer
MOOD_CHIPS = {
    '😭 грустно':      ('xxxtentacion', 'Грустные треки подобраны — пусть музыка поможет.'),
    '🚀 тренировка':   ('phonk', 'Заряд для тренировки — вперёд!'),
    '❤️ романтика':    ('Cigarettes After Sex', 'Романтические треки — наслаждайся.'),
    '☕️ расслабление': ('lofi', 'Расслабься — музыка уже играет.'),
    '😊 радость':      ('beabadoobee', 'Позитивные треки — хорошего настроения!'),
    '🎉 вечеринка':    ('PSY', 'Треки для вечеринки — погнали!'),
}

# Старый словарь для текстового ввода настроения
MOOD_QUERIES = {
    'грустно': "xxxtentacion",
    'счастлив': "beabadoobee",
    'злой': "metal aggressive",
    'романтич': "Cigarettes After Sex",
    'работа': "lofi",
    'тренировк': "phonk",
}

MAIN_CHIPS = ["❔ помощь", "🎶 совет", "🎭 настроение", "🔎 найти трек", "📚 избранное"]
SEARCH_CHIPS = ["🔎 найти трек", "🎶 совет", "🎭 настроение"]

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


def _lastfm_bio(artist_name):
    """Биография артиста через Last.fm artist.getInfo."""
    try:
        params = {
            'method': 'artist.getInfo',
            'artist': artist_name,
            'api_key': LASTFM_API_KEY,
            'format': 'json',
            'lang': 'ru',
        }
        r = requests.get(LASTFM_BASE, params=params, timeout=LASTFM_TIMEOUT)
        if r.status_code != 200:
            return None, []
        data = r.json()
        artist_data = data.get('artist', {})
        if not artist_data:
            return None, []

        # Биография
        bio_raw = artist_data.get('bio', {}).get('summary', '') or ''
        # Убираем ссылку Last.fm в конце (<a href=...>Read more...</a>)
        bio_clean = re.sub(r'<a\s[^>]*>.*?</a>', '', bio_raw, flags=re.IGNORECASE | re.DOTALL).strip()
        bio_clean = re.sub(r'\s+', ' ', bio_clean).strip()
        if len(bio_clean) < 60:
            bio_clean = None
        else:
            # Берём первые 3 предложения
            sentences = bio_clean.split('. ')
            bio_clean = '. '.join(sentences[:3]).strip()
            if bio_clean and not bio_clean.endswith('.'):
                bio_clean += '.'

        # Похожие артисты для чипсов
        similar_raw = artist_data.get('similar', {}).get('artist', [])
        similar = [a['name'] for a in similar_raw[:3] if a.get('name')]

        return bio_clean, similar
    except Exception:
        return None, []


def _reply(text, tracks=None, suggestions=None):
    return {
        "text": text,
        "tracks": tracks or [],
        "suggestions": suggestions or MAIN_CHIPS,
    }


def process_message(text: str, user=None) -> dict:
    if not text or not text.strip():
        return _reply("Напиши что-нибудь! Я слушаю.")

    msg = text.strip().lower()

    # 0. Чипсы настроения (первый приоритет — конкретный выбор)
    if msg in MOOD_CHIPS:
        deezer_query, mood_text = MOOD_CHIPS[msg]
        tracks = _deezer_search(deezer_query, limit=5)
        return _reply(
            mood_text,
            tracks=tracks,
            suggestions=["🔄 обновить", "🎭 другое настроение", "🔎 найти трек"]
        )

    # Обновить треки — повтор последнего настроения (простой рефреш через совет)
    if msg in ('🔄 обновить треки', '🔄 обновить'):
        tracks = _deezer_search("top hits popular", limit=5)
        return _reply("Вот новая подборка:", tracks=tracks, suggestions=["🔄 обновить", "🎭 другое настроение", "🔎 найти трек"])

    if msg in ('🎭 другое настроение',):
        msg = 'настроение'  # fall through к блоку настроения ниже

    # 1. Приветствие
    if any(g in msg for g in GREETINGS):
        name = f", {user.username}" if user and user.is_authenticated else ""
        return _reply(
            f"Привет{name}! Я Music Assistant. Чем помочь?",
            suggestions=MAIN_CHIPS
        )

    # 2. До свидания
    if any(b in msg for b in BYE_KEYWORDS):
        return _reply("Пока! Возвращайся за хорошей музыкой.", suggestions=MAIN_CHIPS)

    # 3. Спасибо
    if any(t in msg for t in THANKS_KEYWORDS):
        return _reply("Пожалуйста! Рад помочь.", suggestions=MAIN_CHIPS)

    # 4. Помощь
    if any(h in msg for h in HELP_KEYWORDS):
        return _reply(HELP_TEXT, suggestions=["🎶 совет", "🎭 настроение", "🔎 найти трек", "топ треков", "кто такой", "📚 избранное"])

    # 5. Очистка
    if 'очисти' in msg or 'очистить' in msg or 'сбрось' in msg or 'сбросить' in msg or 'очистка' in msg or 'сброс' in msg or 'clear' in msg:
        return _reply("__clear__")

    # 6. Статистика избранных
    if any(w in msg for w in ['избранн', 'сколько треков', 'моих треков', 'моя библиотека', '📚 избранное']):
        if user and user.is_authenticated:
            count = user.songs.filter(is_favorite=True).count()
            if count == 0:
                return _reply("У тебя пока нет избранных треков.", suggestions=["найди трек", "совет"])
            word = "трек" if count == 1 else "трека" if 2 <= count <= 4 else "треков"
            return _reply(f"У тебя {count} {word} в избранном.", suggestions=["найди трек", "совет"])
        return _reply("Войди в аккаунт, чтобы я мог показать твою библиотеку.")

    # 7. Настроение — показываем меню выбора
    if 'настроение' in msg or msg == '🎭 настроение':
        return _reply(
            "Выбери под какое настроение подобрать музыку:",
            suggestions=["😭 грустно", "🚀 тренировка", "❤️ романтика", "☕️ расслабление", "😊 радость", "🎉 вечеринка", "🔙 назад"]
        )

    # 8. Кнопка "Назад"
    if msg in ('🔙 назад', 'назад'):
        return _reply("Главное меню:", suggestions=MAIN_CHIPS)

    # 9. Совет / рекомендация
    if any(w in msg for w in ['совет', 'порекомендуй', 'что послушать', 'посоветуй', 'рекомендация']):
        rec = RECOMMENDATIONS[_rec_idx[0] % len(RECOMMENDATIONS)]
        _rec_idx[0] += 1
        tracks = _deezer_search(f"{rec[0]} {rec[1]}", limit=4)
        return _reply(
            f"Рекомендую: {rec[0]} — {rec[1]}",
            tracks=tracks,
            suggestions=["ещё совет", "найди трек", f"кто такой {rec[1]}", "назад"]
        )

    # 10. Ещё совет
    if ('ещё' in msg and 'совет' in msg) or msg == '🎶 ещё совет':
        rec = RECOMMENDATIONS[_rec_idx[0] % len(RECOMMENDATIONS)]
        _rec_idx[0] += 1
        tracks = _deezer_search(f"{rec[0]} {rec[1]}", limit=4)
        return _reply(f"Рекомендую: {rec[0]} — {rec[1]}", tracks=tracks, suggestions=["ещё совет", "найди трек"])

    # 11. Жанр
    for genre, info in GENRE_INFO.items():
        if genre in msg:
            tracks = _deezer_search(genre, limit=4)
            return _reply(
                f"{genre.capitalize()}\n\n{info}",
                tracks=tracks,
                suggestions=[f"топ треков {genre}", "совет", "помощь"]
            )

    # 12. Кто такой / биография — Last.fm
    if re.search(r'кто такой|кто такая|расскажи про|расскажи о|биография|инфо о', msg):
        query = re.sub(r'кто такой|кто такая|расскажи про|расскажи о|биография|инфо о', '', msg).strip()
        if not query:
            return _reply("Напиши имя артиста, например: кто такой Drake")

        bio, similar = _lastfm_bio(query)
        tracks = _deezer_search(query, limit=4)

        # Чипсы: топ треков + похожие артисты
        chips = [f"топ треков {query}"]
        chips += [f"кто такой {s}" for s in similar[:2]]
        chips.append("совет")

        if bio:
            return _reply(bio, tracks=tracks, suggestions=chips)
        elif tracks:
            return _reply(f"Вот треки артиста {query.title()}:", tracks=tracks, suggestions=chips)
        return _reply(f"Не нашел информации о {query}.", suggestions=MAIN_CHIPS)

    # 13. Топ треков
    if 'топ' in msg or 'лучшие треки' in msg or 'хиты' in msg:
        query = re.sub(r'топ треков|топ|лучшие треки|хиты', '', msg).strip()
        if not query:
            return _reply("Напиши имя артиста: топ треков Eminem", suggestions=["топ треков Drake", "топ треков Eminem"])
        tracks = _deezer_search(f'artist:"{query}"', limit=5) or _deezer_search(query, limit=5)
        return _reply(f"Топ треков {query.title()}:", tracks=tracks, suggestions=["совет", f"кто такой {query}"])

    # 14. Найти исполнителя
    if re.search(r'найди исполнителя|найди артиста|исполнитель', msg):
        query = re.sub(r'найди исполнителя|найди артиста|исполнитель', '', msg).strip()
        if not query:
            return _reply("Напиши имя артиста.")
        tracks = _deezer_search(query, limit=5)
        return _reply(f"Треки артиста {query.title()}:", tracks=tracks, suggestions=[f"кто такой {query}", "совет"])

    # 15. Найти трек
    if re.search(r'найди трек|найди песню|поищи|найди|🔍 найди трек|🔎 найти трек', msg):
        query = re.sub(r'найди трек|найди песню|поищи трек|поищи|найди|🔍 найди трек', '', msg).strip()
        if not query:
            return _reply("Напиши название трека.", suggestions=SEARCH_CHIPS)
        tracks = _deezer_search(query, limit=5)
        if tracks:
            return _reply(f"Результаты поиска «{query}»:", tracks=tracks, suggestions=["🎶 ещё совет", "❔ помощь", "🎭 настроение"])
        return _reply(f"Ничего не нашел по запросу «{query}».", suggestions=["🔎 найти трек", "❔ помощь", "🎭 настроение"])

    # 16. Текстовое настроение
    for mood_key, mood_query in MOOD_QUERIES.items():
        if mood_key in msg:
            tracks = _deezer_search(mood_query, limit=4)
            return _reply("Подобрал треки под настроение:", tracks=tracks, suggestions=["🎭 настроение", "ещё совет", "найди трек"])

    # 17. Что играет
    if 'что играет' in msg or 'что сейчас' in msg:
        return _reply("Нажми на любой трек — он сразу начнет играть!", suggestions=MAIN_CHIPS)

    # 18. Fallback
    if len(msg) > 2:
        tracks = _deezer_search(msg, limit=3)
        if tracks:
            return _reply(f"Вот что нашел по запросу «{text.strip()}»:", tracks=tracks, suggestions=["помощь", "совет", "назад"])

    return _reply(
        "Не совсем понял. Попробуй:\n- найди трек [название]\n- кто такой [артист]\n- 🎭 настроение\n- помощь",
        suggestions=MAIN_CHIPS
    )