import requests
from bs4 import BeautifulSoup
import json
import random
import time
from datetime import date

# Sources para streams
SOURCES = [
    'https://stream2watch.sx',
    'https://sportsurge.net',
    'https://footybite.to',
    'https://totalsportek.pro',
    'https://viprow.me',
    'https://livetv.sx',
    'https://buffstreams.app',
    'https://crackstreams.me',
    'https://vipleague.tv',
    'https://bosscast.net'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
]

def scrape_streams(event_name, league, lang='es', country='global'):
    streams = []
    sampled_sources = random.sample(SOURCES, min(3, len(SOURCES)))  # Solo 3 para rápido
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    for source in sampled_sources:
        try:
            search_query = f"{event_name} {league} {lang} {country}".replace(' ', '+')
            url = f"{source}/?s={search_query}" if '?' not in source else f"{source}&s={search_query}"
            r = requests.get(url, headers=headers, timeout=5)  # Timeout corto
            soup = BeautifulSoup(r.text, 'html.parser')
            # Busca links con m3u8/hls/stream
            elements = soup.find_all('a', href=True) + soup.find_all('iframe', src=True)
            for elem in elements[:1]:  # 1 por source
                attr = elem.get('href') or elem.get('src')
                if attr and 'http' in attr and ('m3u8' in attr or 'hls' in attr or 'stream' in attr.lower()):
                    # Agrega token si no tiene
                    if '?' not in attr:
                        attr += f"?token={random.randint(100000,999999)}&expires={int(time.time()) + 1800}"
                    streams.append({
                        'source': source,
                        'url': attr,
                        'lang': lang,
                        'country': country,
                        'league_filter': league
                    })
                    break
            time.sleep(1)  # Delay anti-ban
            if len(streams) >= 3:
                break
        except Exception as e:
            print(f"Error en {source}: {e}")
            continue
    # Fallback si 0 streams
    if not streams:
        streams = [{
            'source': 'fallback',
            'url': f"https://example-stream.m3u8?token={random.randint(100000,999999)}&expires={int(time.time()) + 1800}",
            'lang': lang,
            'country': country,
            'league_filter': league
        }]
    return streams

def run_scraper():
    today = '2025-11-03'  # Hoy
    # TheSportsDB para events fútbol/baloncesto
    url_football = f"http://www.thesportsdb.com/api/v1/json/123/eventsday.php?d={today}&s=Football"
    url_basketball = f"http://www.thesportsdb.com/api/v1/json/123/eventsday.php?d={today}&s=Basketball"
    r_football = requests.get(url_football)
    r_basketball = requests.get(url_basketball)
    events_football = r_football.json().get('events', []) or []
    events_basketball = r_basketball.json().get('events', []) or []
    events = events_football + events_basketball
    
    agenda = []
    for event in events[:5]:  # Solo 5 para test rápido
        event_id = event['idEvent']
        event_name = event['strEvent']
        league = event['strLeague']
        date_event = event['dateEvent']
        score = None
        detail_url = f"http://www.thesportsdb.com/api/v1/json/123/lookupevent.php?i={event_id}"
        detail_r = requests.get(detail_url)
        try:
            detail_json = detail_r.json()
            if isinstance(detail_json, dict):
                detail = detail_json.get('events', [{}])[0]
                home_score = detail.get('intHomeScore')
                away_score = detail.get('intAwayScore')
                if home_score is not None and away_score is not None:
                    score = f"{home_score} - {away_score}"
        except:
            score = None
        streams = scrape_streams(event_name, league)
        agenda.append({
            'id': event_id,
            'event': event_name,
            'league': league,
            'date': date_event,
            'score': score,
            'streams': streams
        })
        time.sleep(1)
    
    with open('agenda.json', 'w') as f:
        json.dump(agenda, f, indent=2)
    print(f"Scraped {len(agenda)} events con streams a agenda.json")

if __name__ == "__main__":
    run_scraper()
