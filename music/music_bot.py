"""
music_bot.py — логика Music Assistant
Обрабатывает 15+ типов запросов, использует Deezer API для поиска треков.
"""
import re
from urllib.parse import quote_plus

import requests

DEEZER_TIMEOUT = 8

# ── Шаблоны приветствий / помощи ──────────────────────────────────────────────
GREETINGS = {'привет', 'хай', 'здравствуй', 'hello', 'hi', 'хелло', 'йоу', 'ку'}
HELP_KEYWORDS = {'помощь', 'помоги', 'help', 'что умеешь', 'команды', 'что ты умеешь'}
BYE_KEYWORDS = {'пока', 'до свидания', 'bye', 'выход', 'бывай', 'чао'}
THANKS_KEYWORDS = {'спасибо', 'благодарю', 'thanks', 'thank you', 'спс', 'благодарствую'}

HELP_TEXT = """🎵 Я Music Assistant — твой музыкальный помощник!

Вот что я умею:
• **Найди трек** [название] — поищу трек по названию
• **Найди исполнителя** [имя] — треки артиста
• **Топ треков** [исполнитель] — популярные треки
• **Что такое [жанр/стиль]** — расскажу о музыкальном жанре
• **Совет** — порекомендую что послушать
• **Сколько у меня избранных** — покажу статистику
• **Очисти историю чата** — сброс диалога
• **Кто такой [артист]** — информация об исполнителе
• **Помощь** — это меню

Просто напиши что хочешь — я пойму! 🎧"""

GENRE_INFO = {
    'поп': 'Поп-музыка — популярная музыка с простыми мелодиями и запоминающимися припевами. Главные звёзды: Тейлор Свифт, Ed Sheeran, Ариана Гранде.',
    'рок': 'Рок — музыкальный жанр с гитарами, ударными и энергичным звуком. От The Beatles до Metallica — рок охватывает десятки поджанров.',
    'хип-хоп': 'Хип-хоп зародился в 70-х в Нью-Йорке. Рэп, брейкданс, диджеинг — его основные элементы. Дрейк, Кендрик Ламар, Эминем — топ-артисты.',
    'хипхоп': 'Хип-хоп зародился в 70-х в Нью-Йорке. Рэп, брейкданс, диджеинг — его основные элементы. Дрейк, Кендрик Ламар, Эминем — топ-артисты.',
    'джаз': 'Джаз — импровизационный жанр, зародившийся в начале XX века в США. Майлс Дэвис, Джон Колтрейн, Луи Армстронг — легенды жанра.',
    'классика': 'Классическая музыка — многовековая традиция от Баха до Шостаковича. Симфонии, концерты, оперы — формы этого жанра.',
    'электронная': 'Электронная музыка создаётся синтезаторами и компьютерами. House, Techno, EDM — главные поджанры. Daft Punk, Avicii, Calvin Harris.',
    'r&b': 'R&B (Rhythm and Blues) — душевная музыка с элементами соула. Уикнд, Бейонсе, Фрэнк Оушен — современные флагманы жанра.',
    'металл': 'Метал — тяжёлая гитарная музыка с мощным звуком. От Iron Maiden до Slipknot — тысячи поджанров.',
    'кантри': 'Кантри — американская народная музыка с гитарами и историями о жизни. Джонни Кэш, Дольли Партон, Морган Уоллен.',
    'латин': 'Латинская музыка включает сальсу, реггетон, бачату. Бад Банни, Малума, J Balvin — суперзвёзды жанра.',
}

ARTIST_INFO = {
    'дрейк': 'Drake (Обри Грэм) — канадский рэпер и певец, один из самых продаваемых артистов в истории. Треки: God\'s Plan, Hotline Bling, One Dance.',
    'эминем': 'Eminem — легендарный рэпер из Детройта, считается одним из лучших MC всех времён. Альбомы: The Slim Shady LP, The Marshall Mathers LP.',
    'тейлор свифт': 'Taylor Swift — певица и автор песен, одна из самых успешных поп-артисток. Альбомы: 1989, Folklore, Midnights.',
    'the weeknd': 'The Weeknd (Абель Тесфайе) — канадский певец, известный тёмным R&B звуком. Треки: Blinding Lights, Starboy, Save Your Tears.',
    'weeknd': 'The Weeknd (Абель Тесфайе) — канадский певец, известный тёмным R&B звуком. Треки: Blinding Lights, Starboy, Save Your Tears.',
    'billie eilish': 'Billie Eilish — певица, ставшая звездой в 17 лет. Известна треком Bad Guy и саундтреком к Бонду.',
    'биллиш': 'Billie Eilish — певица, ставшая звездой в 17 лет. Известна треком Bad Guy и саундтреком к Бонду.',
}

RECOMMENDATIONS = [
    '🎵 Попробуй послушать "Blinding Lights" от The Weeknd — абсолютный хит!',
    '🎸 Если любишь рок — "Bohemian Rhapsody" от Queen никогда не устаревает.',
    '🎧 "God\'s Plan" от Drake — один из самых популярных треков последнего десятилетия.',
    '🌊 В настроении для расслабления? Попробуй "Weightless" от Marconi Union.',
    '⚡ Для заряда энергии: "Eye of the Tiger" от Survivor или "Thunderstruck" от AC/DC.',
    '🌙 Вечерний mood: "Midnight Rain" от Taylor Swift или "Starboy" от The Weeknd.',
    '🔥 Горячий хит: попробуй последние треки Бада Банни или Bad Bunny — он ломает рекорды!',
]

_rec_idx = [0]


def _deezer_search(query, limit=5):
    """Поиск треков в Deezer API."""
    try:
        url = f"https://api.deezer.com/search?q={quote_plus(query)}&limit={limit}"
        r = requests.get(url, timeout=DEEZER_TIMEOUT)
        r.raise_for_status()
        return r.json().get('data', [])
    except Exception:
        return []


def _format_tracks(tracks, prefix=''):
    """Форматирует список треков в текст."""
    if not tracks:
        return 'Ничего не нашлось 😔 Попробуй другой запрос.'
    lines = [prefix] if prefix else []
    for i, t in enumerate(tracks, 1):
        title = t.get('title', '?')
        artist = t.get('artist', {}).get('name', '?')
        preview = t.get('preview', '')
        play_hint = ' ▶' if preview else ' (нет превью)'
        lines.append(f"{i}. **{title}** — {artist}{play_hint}")
    lines.append('\n_Найди эти треки через поиск на главной странице!_')
    return '\n'.join(lines)


def process_message(text: str, user=None) -> str:
    """
    Главная функция: принимает текст сообщения, возвращает ответ бота.
    """
    if not text or not text.strip():
        return 'Напиши что-нибудь! Я слушаю 🎧'

    msg = text.strip().lower()

    # 1. Приветствие
    if any(g in msg for g in GREETINGS):
        name = f', {user.username}' if user and user.is_authenticated else ''
        return f'Привет{name}! 🎵 Я Music Assistant. Чем могу помочь? Напиши **помощь** чтобы узнать мои возможности.'

    # 2. До свидания
    if any(b in msg for b in BYE_KEYWORDS):
        return 'Пока! 🎵 Возвращайся, если захочешь найти хорошую музыку!'

    # 3. Спасибо
    if any(t in msg for t in THANKS_KEYWORDS):
        return 'Пожалуйста! 😊 Рад помочь с музыкой. Если нужно что-то ещё — спрашивай!'

    # 4. Помощь
    if any(h in msg for h in HELP_KEYWORDS):
        return HELP_TEXT

    # 5. Очистить историю (обрабатывается во view, сюда не дойдёт)
    if 'очисти' in msg or 'очистить' in msg or 'сбрось' in msg:
        return '__clear__'

    # 6. Статистика избранных
    if any(w in msg for w in ['избранн', 'сколько треков', 'моих треков', 'моя библиотека']):
        if user and user.is_authenticated:
            count = user.songs.filter(is_favorite=True).count()
            if count == 0:
                return 'У тебя пока нет избранных треков. Иди на главную и добавь! ❤️'
            return f'У тебя **{count}** {'трек' if count == 1 else 'треков' if 2 <= count <= 4 else 'треков'} в избранном! 🎵 Смотри их в разделе [Избранное](/favorites/).'
        return 'Войди в аккаунт, чтобы я мог показать твою библиотеку. [Войти](/login/) 🔑'

    # 7. Совет / рекомендация
    if any(w in msg for w in ['совет', 'порекомендуй', 'что послушать', 'посоветуй', 'рекомендация']):
        rec = RECOMMENDATIONS[_rec_idx[0] % len(RECOMMENDATIONS)]
        _rec_idx[0] += 1
        return rec

    # 8. Жанр
    for genre, info in GENRE_INFO.items():
        if genre in msg:
            return f'🎼 **{genre.capitalize()}**\n\n{info}'

    # 9. Артист (кто такой)
    if 'кто такой' in msg or 'кто такая' in msg or 'расскажи про' in msg or 'расскажи о' in msg:
        for artist_key, info in ARTIST_INFO.items():
            if artist_key in msg:
                return f'🎤 {info}'
        # Попробуем поискать через Deezer
        # Убираем служебные слова
        query = re.sub(r'кто такой|кто такая|расскажи про|расскажи о', '', msg).strip()
        if query:
            tracks = _deezer_search(query, limit=3)
            if tracks:
                artist_name = tracks[0].get('artist', {}).get('name', query)
                return f'🎤 Нашёл треки артиста **{artist_name}**:\n' + _format_tracks(tracks)
        return 'Не знаю такого артиста 😅 Попробуй поискать на главной странице!'

    # 10. Топ треков исполнителя
    if 'топ' in msg or 'лучшие треки' in msg or 'хиты' in msg:
        query = re.sub(r'топ треков|топ|лучшие треки|хиты|исполнителя', '', msg).strip()
        if not query:
            return 'Напиши имя артиста, например: **топ треков Eminem**'
        tracks = _deezer_search(f'artist:"{query}"', limit=5)
        if not tracks:
            tracks = _deezer_search(query, limit=5)
        return _format_tracks(tracks, prefix=f'🔥 Топ треков **{query.title()}**:')

    # 11. Найти исполнителя
    if re.search(r'найди исполнителя|найди артиста|исполнитель', msg):
        query = re.sub(r'найди исполнителя|найди артиста|исполнитель', '', msg).strip()
        if not query:
            return 'Напиши имя артиста, например: **найди исполнителя Drake**'
        tracks = _deezer_search(query, limit=5)
        return _format_tracks(tracks, prefix=f'🎤 Треки артиста **{query.title()}**:')

    # 12. Найти трек
    if re.search(r'найди трек|найди песню|поищи|найди|трек|песня', msg):
        query = re.sub(r'найди трек|найди песню|поищи трек|поищи|найди', '', msg).strip()
        if not query:
            return 'Напиши название трека, например: **найди трек Blinding Lights**'
        tracks = _deezer_search(query, limit=5)
        return _format_tracks(tracks, prefix=f'🎵 Результаты поиска «{query}»:')

    # 13. Настроение / mood
    mood_map = {
        'грустн': 'Для грустного настроения: Adele — Someone Like You, Lewis Capaldi — Someone You Loved, Billie Eilish — when the party\'s over',
        'счастлив': 'Для счастливого настроения: Pharrell Williams — Happy, Katy Perry — Roar, Justin Timberlake — Can\'t Stop the Feeling',
        'злой': 'Для выброса агрессии: Linkin Park — In The End, Eminem — Lose Yourself, Rage Against The Machine — Killing In The Name',
        'романтич': 'Для романтики: Ed Sheeran — Perfect, John Legend — All of Me, Bruno Mars — Just The Way You Are',
        'работа': 'Для работы/учёбы: Hans Zimmer OSTs, lo-fi hip hop, Daft Punk — Get Lucky',
        'тренировк': 'Для тренировки: Eye of the Tiger, Eminem — Till I Collapse, AC/DC — Thunderstruck',
    }
    for mood_key, mood_rec in mood_map.items():
        if mood_key in msg:
            return f'🎵 {mood_rec}'

    # 14. Что играет (у нас нет real-time данных, объясняем)
    if 'что играет' in msg or 'что сейчас' in msg or 'играет сейчас' in msg:
        return 'Я не знаю что именно играет у тебя сейчас 😅 Но ты можешь нажать на любой трек в списке и он начнёт играть! Используй поиск на главной странице 🎵'

    # 15. Если ничего не подошло — пробуем поискать в Deezer
    if len(msg) > 2:
        tracks = _deezer_search(msg, limit=3)
        if tracks:
            return _format_tracks(tracks, prefix=f'🔍 Вот что нашёл по запросу «{text.strip()}»:')

    # 16. Дефолтный ответ
    return (
        'Не совсем понял тебя 🤔 Попробуй:\n'
        '• **найди трек** [название]\n'
        '• **найди исполнителя** [имя]\n'
        '• **совет** — что послушать\n'
        '• **помощь** — все команды'
    )
