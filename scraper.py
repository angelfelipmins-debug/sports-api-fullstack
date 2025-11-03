import requests
from bs4 import BeautifulSoup
import json
import random
import time

# Sites y search URLs
SITES = {
    'cuevana': {
        'base_url': 'https://cuevana3.me',
        'search_url': 'https://cuevana3.me/search/{query}'
    },
    'pelisplus': {
        'base_url': 'https://pelisplus.so',
        'search_url': 'https://pelisplus.so/?s={query}'
    },
    'hackstore': {
        'base_url': 'https://hackstore.tv',
        'search_url': 'https://hackstore.tv/search/{query}'
    }
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
]

def scrape_site(site_name, query):
    site = SITES[site_name]
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        search_url = site['search_url'].format(query=query.replace(' ', '+'))
        r = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Extract first result (ajusta selectors si cambia site)
        item = soup.find('div', class_='movie-item') or soup.find('article', class_='post') or soup.find('li', class_='movie')
        if not item:
            return None
        
        title = item.find('h2') or item.find('h3') or item.find('a')
        title = title.text.strip() if title else 'N/A'
        
        year = 'N/A'
        year_elem = item.find('span', class_='year') or item.find('small')
        if year_elem:
            year = year_elem.text.strip()
        
        genre = 'N/A'
        genre_elem = item.find('span', class_='genre') or item.find('p', class_='genres')
        if genre_elem:
            genre = genre_elem.text.strip()
        
        link_elem = item.find('a', href=True)
        link = site['base_url'] + link_elem['href'] if link_elem else 'N/A'
        
        # Poster URL
        poster_elem = item.find('img', src=True)
        poster = poster_elem['src'] if poster_elem else 'N/A'
        
        # Stream URL (de detail page, si visible)
        stream = 'N/A'
        if link != 'N/A':
            detail_r = requests.get(link, headers=headers, timeout=5)
            detail_soup = BeautifulSoup(detail_r.text, 'html.parser')
            stream_elem = detail_soup.find('iframe', src=True) or detail_soup.find('video', src=True) or detail_soup.find('a', href=True, text='Ver ahora')
            if stream_elem:
                stream = stream_elem.get('src') or stream_elem.get('href') or 'N/A'
                if stream and '?' not in stream:
                    stream += f"?token={random.randint(100000,999999)}&expires={int(time.time()) + 1800}"  # Mock token
            time.sleep(1)  # Delay
        
        return {
            'site': site_name,
            'title': title,
            'year': year,
            'genre': genre,
            'link': link,
            'poster': poster,
            'stream_url': stream
        }
    except Exception as e:
        print(f"Error en {site_name}: {e}")
        return None

def scrape_movies(query, num_sites=3):
    results = []
    for site_name in list(SITES.keys())[:num_sites]:
        result = scrape_site(site_name, query)
        if result:
            results.append(result)
        time.sleep(2)  # Delay anti-ban
    return results

if __name__ == "__main__":
    query = input("Nombre de la película: ") or "Inception"
    movies = scrape_movies(query)
    with open('movies.json', 'w') as f:
        json.dump(movies, f, indent=2)
    print(f"Scraped {len(movies)} resultados a movies.json")
    print(json.dumps(movies, indent=2))
