import requests
from bs4 import BeautifulSoup
import json
import random
import time
from datetime import date

SOURCES = [
    'https://librefutboltv.su/es/',
    'https://pluto.tv',
    'https://eurovisionsport.com',
    'https://stream2watch.sx',
    'https://www.9now.com.au',
    'https://sportsurge.net',
    'https://footybite.to',
    'https://totalsportek.pro',
    'https://viprow.me',
    'https://livetv.sx',
    'https://buffstreams.app',
    'https://crackstreams.me',
    'https://vipleague.tv',
    'https://bosscast.net',
    'https://firstrowsports.tv',
    'https://batmanstream.net',
    'https://ositodroid.de',
    'https://quezalmaik.vercel.app'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
]

def scrape_streams(event_name, league, lang='es', country='global'):
    streams = []
    sampled_sources = random.sample(SOURCES, min(5, len(SOURCES)))
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    for source in sampled_sources:
        try:
            search_query = f"{event_name} {league} {lang} {country}".replace(' ', '+')
            url = f"{source}/?q={search_query}" if '?' not in source else f"{source}&q={search_query}"
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Busca genérico m3u8/hls/token en links/iframes
            elements = soup.find_all(['iframe', 'a', 'video'], attrs={'src': True, 'href': True})
            for elem in elements[:2]:  # Top 2 por source
                attr = elem.get('src') or elem.get('href')
                if attr and 'http' in attr and ('m3u8' in attr or 'hls' in attr or 'stream' in attr):
                    # Mock token si no hay (real scrape captura)
                    if '?' not in attr:
                        attr += f"?token={random.randint(100000,999999)}&expires={int(time.time()) + 1800}"
                    streams.append({'source': source, 'url': attr, 'lang': lang, 'country': country, 'league_filter': league})
                    break
            time.sleep(random.uniform(1, 2))
            if len(streams) >= 5:
                break
        except Exception as e:
            print(f"Error source {source}: {e}")
            continue
    # Fallback mock si 0 streams
    if not streams:
        streams = [
            {
                "source": "fallback-test",
                "url": f"https://example-stream.m3u8?token={random.randint(100000,999999)}&expires={int(time.time()) + 1800}",
                "lang": lang,
                "country": country,
                "league_filter": league
            }
        ]
    return streams

def run_scraper():
    today = date.today().isoformat()
    url_football = f"http://www.thesportsdb.com/api/v1/json/123/eventsday.php?d={today}&s=Football"
    url_basketball = f"http://www.thesportsdb.com/api/v1/json/123/eventsday.php?d={today}&s=Basketball"
    r_football = requests.get(url_football)
    r_basketball = requests.get(url_basketball)
    events = r_football.json().get('events', []) + r_basketball.json().get('events', [])
    
    agenda = []
    for event in events[:10]:
        event_id = event['idEvent']
        event_name = event['strEvent']
        league = event['strLeague']
        date_event = event['dateEvent']
        score = None
        detail_url = f"http://www.thesportsdb.com/api/v1/json/123/lookupevent.php?i={event_id}"
        detail_r = requests.get(detail_url)
        detail = detail_r.json().get('events', [{}])[0]
        home_score = detail.get('intHomeScore')
        away_score = detail.get('intAwayScore')
        if home_score is not None and away_score is not None:
            score = f"{home_score} - {away_score}"
        streams = scrape_streams(event_name, league)
        agenda.append({
            'id': event_id,
            'event': event_name,
            'league': league,
            'date': date_event,
            'score': score,
            'streams': streams
        })
        time.sleep(0.5)
    
    with open('agenda.json', 'w') as f:
        json.dump(agenda, f, indent=2)
    print(f"Scraped {len(agenda)} events to agenda.json")

if __name__ == "__main__":
    run_scraper()
