from datetime import datetime
from old_project.config import FILENAME
import json

def load():
    try:
        with open(FILENAME, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save(songs):
    with open(FILENAME, "w", encoding="utf-8") as file:
        json.dump(songs, file, indent=4, ensure_ascii=False)

def add(songs):
    title = input("Название: ")
    artist = input("Исполнитель: ")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_song = {"title": title, "artist": artist, "added_at": timestamp}
    songs.append(new_song)

    save(songs)
    print(f"Песня добавлена ({timestamp}).")

def search(songs, query):
    query = query.lower()
    found_any = False
    for song in songs:
        if query in song['title'].lower() or query in song['artist'].lower():
            print(f"Найдено: {song['title']} - {song['artist']}")
            found_any = True
    
    if not found_any:
        print("Ничего не найдено по вашему запросу.")


def delete(songs, index):
    try:
        deleted_song = songs.pop(index - 1)
        save(songs)
        print(f"Песня {deleted_song['title']} удалена")
    except IndexError:
        print("Error Песни с таким номером нет")

def redact(songs, index):
    try:
        # Получаем текущую песню, чтобы показать старые данные
        current_song = songs[index - 1]
        
        print(f"--- Редактирование (Enter, чтобы оставить без изменений) ---")
        
        new_title = input(f"Новое название [{current_song['title']}]: ")
        if new_title: # Если ввод не пустой, обновляем
            current_song['title'] = new_title
            
        new_artist = input(f"Новый артист [{current_song['artist']}]: ")
        if new_artist: # Если ввод не пустой, обновляем
            current_song['artist'] = new_artist
            
        save(songs)
        print("Песня успешно обновлена!")
    except IndexError:
        print("Ошибка: Песни с таким номером нет.")

def show_songs(songs):
    print("\n--- Список всех песен ---")
    for index, song in enumerate(songs, 1):
        artist = song['artist']
        title = song['title']

        print(f"{index}. {artist} — {title}")
def sort(songs, n):
    if n == "1":
        songs.sort(key=lambda x: x['artist'].lower())
    if n == "2":
        songs.sort(key=lambda x: x['title'].lower())
    elif n == "3":
        songs.sort(key=lambda x: x['added_at'], reverse=True)
    save(songs)
    print("Список отсортирован!")