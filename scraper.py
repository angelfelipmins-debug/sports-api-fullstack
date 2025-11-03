import requests
from bs4 import BeautifulSoup
import json
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from pyvirtualdisplay import Display

SOURCES = [
    'https://librefutboltv.su/es/',
    'https://www.bbc.co.uk/iplayer',
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

def get_proxies():
    try:
        r = requests.get('https://free-proxy-list.net/', timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        proxies = []
        table = soup.find('table', {'id': 'proxylisttable'})
        if table:
            for row in table.find_all('tr')[1:20]:
                tds = row.find_all('td')
                if len(tds) > 6 and tds[6].text.strip() == 'yes':
                    proxy = f"{tds[1].text}:{tds[2].text}"
                    proxies.append(proxy)
        return proxies if proxies else ['127.0.0.1:8080']
    except:
        return ['127.0.0.1:8080']

def setup_driver(proxy=None):
    display = Display(visible=0, size=(800, 600))
    display.start()
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    if proxy:
        options.add_argument(f'--proxy-server=http://{proxy}')
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_streams(event_name, league, proxies, lang='es', country='global'):  # Fix: proxies antes de defaults
    streams = []
    sampled_sources = random.sample(SOURCES, min(5, len(SOURCES)))
    for source in sampled_sources:
        try:
            proxy = random.choice(proxies)
            driver = setup_driver(proxy)
            search_query = f"{event_name} {league} {lang} {country}".replace(' ', '+')
            url = f"{source}/?q={search_query}" if '?' not in source else f"{source}&q={search_query}"
            driver.get(url)
            wait = WebDriverWait(driver, 5)
            elements = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='stream'], a[href*='m3u8'], a[href*='hls'], video source")
            if elements:
                attr = elements[0].get_attribute('src') or elements[0].get_attribute('href')
                if attr and 'http' in attr:
                    streams.append({'source': source, 'url': attr, 'lang': lang, 'country': country, 'league_filter': league})
            driver.quit()
            time.sleep(random.uniform(1, 2))
            if len(streams) >= 5:
                break
        except (TimeoutException, WebDriverException):
            try:
                driver.quit()
            except:
                pass
            continue
    return streams

def run_scraper():
    proxies = get_proxies()
    today = '2025-11-03'
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
        streams = scrape_streams(event_name, league, proxies)  # Fix: proxies posicional
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
