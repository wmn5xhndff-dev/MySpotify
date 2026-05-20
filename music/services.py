import requests

API_KEY = '953df161bc52776025237474a9bd9b45'
BASE_URL = "http://ws.audioscrobbler.com/2.0/"

def search_song_lastfm(title, artist):
    params = {
        'method': 'track.getInfo',
        'api_key': API_KEY,
        'artist': artist,
        'track': title,
        'format': 'json'
    }
    
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        # Вытягиваем ссылку на обложку (обычно берем размер 'large' или 'extralarge')
        images = data.get('track', {}).get('album', {}).get('image', [])
        image_url = images[-1]['#text'] if images else None
        
        return image_url
    except Exception as e:
        print(f"Ошибка при поиске в Last.fm: {e}")
        return None