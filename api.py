import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
import redis
from firebase_admin import credentials, firestore, initialize_app
from openai import OpenAI
import asyncio
from scraper import run_scraper, get_proxies, setup_driver, scrape_streams
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://default:AX2PAAIncDJhYTljZjE3MDBlZTQ0MDcyYThkOWVmMDc5MDkwMThmZnAyMzIxNDM@splendid-bullfrog-32143.upstash.io:6379")
cred = credentials.Certificate('firebase_key.json')
initialize_app(cred)
db = firestore.client()
r = redis.from_url(REDIS_URL)
grok_client = OpenAI(base_url="https://api.x.ai/v1", api_key=os.getenv("GROK_API_KEY", "xai-iIp2ZgdNe3goMCVOs45k9vfFFjdrpTPS6k0eh67sfhgvzFwrSkZqgRIZhHXlSXDRWvmczwWQX7jiAzfk"))
app = FastAPI()
scheduler = BackgroundScheduler()
ws_connections = {}

with open('agenda.json', 'r') as f:
    global_agenda = json.load(f)

def filter_agenda(liga=None, idioma=None, pais=None):
    filtered = global_agenda
    if liga:
        filtered = [e for e in filtered if liga.lower() in e['league'].lower()]
    if idioma:
        filtered = [e for e in filtered if any(idioma.lower() in s.get('lang', '').lower() for s in e['streams'])]
    if pais:
        filtered = [e for e in filtered if any(pais.upper() in s.get('country', '').upper() for s in e['streams'])]
    return filtered

async def process_ai_summary(event):
    try:
        response = grok_client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": f"Resumen AI corto del partido: {event['event']} en {event['league']}. Score: {event['score'] or 'Próximo'}."}]
        )
        event['ai_summary'] = response.choices[0].message.content
    except:
        event['ai_summary'] = "Resumen no disponible."
    event['ads'] = True
    event['ad_url'] = "https://example.com/ad.m3u8"

def generate_player_html(event):
    streams_str = json.dumps(event['streams'])
    player_js = f"""
    const streams = {streams_str};
    const video = document.getElementById('video');
    const status = document.getElementById('status');
    const adContainer = document.getElementById('ad-container');
    let hls, currentStreamIndex = 0, refreshInterval;
    function loadStream() {{
        let url = streams[currentStreamIndex].url;
        if (Hls.isSupported()) {{
            if (hls) hls.destroy();
            hls = new Hls();
            hls.loadSource(url);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, () => status.textContent = 'Stream loaded con token');
            hls.on(Hls.Events.ERROR, async (e, d) => {{
                if (d.response?.code === 403) {{
                    status.textContent = 'Token vencido - Refrescando...';
                    const fresh = await fetch('/refresh_token?stream_id=' + currentStreamIndex + '&league=' + streams[0].league_filter);
                    const newUrl = await fresh.text();
                    hls.loadSource(newUrl);
                }} else {{
                    currentStreamIndex = (currentStreamIndex + 1) % streams.length;
                    loadStream();
                }}
            }});
            if (streams[0].ads) {{
                setInterval(() => {{
                    adContainer.style.display = 'block';
                    adContainer.querySelector('iframe').src = streams[0].ad_url + '&refresh=' + Date.now();
                    setTimeout(() => adContainer.style.display = 'none', 30000);
                }}, 300000);
            }}
            refreshInterval = setInterval(async () => {{
                const fresh = await fetch('/refresh_token?stream_id=' + currentStreamIndex + '&league=' + streams[0].league_filter);
                const newUrl = await fresh.text();
                hls.loadSource(newUrl);
            }}, 300000);
        }} else {{
            video.src = url;
        }}
    }}
    loadStream();
    video.addEventListener('loadedmetadata', () => status.textContent += ' - Listo');
    """
    return f"""<!DOCTYPE html><html lang="es"><head><title>Player {event['event']}</title><script src="https://cdn.jsdelivr.net/npm/hls.js@1.4.12"></script></head><body><video id="video" controls width="100%" height="auto" autoplay muted></video><div id="status">Cargando...</div><div id="ad-container" style="display:none;background:gray;height:100px;"><iframe src="" width="100%"></iframe></div><script>{player_js}</script></body></html>"""

@app.get("/api/agenda")
async def debug_agenda():
    try:
        with open('agenda.json', 'r') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except FileNotFoundError:
        return JSONResponse(content={"error": "agenda.json no encontrada – corre scraper primero"}, status_code=404)
async def get_agenda(liga: str = Query(None), idioma: str = Query(None), pais: str = Query(None)):
    key = f"agenda:{liga or ''}:{idioma or ''}:{pais or ''}"
    cached = r.get(key)
    if cached:
        return JSONResponse(content=json.loads(cached))
    query_id = f"q_{abs(hash(f'{liga}_{idioma}_{pais}'))}"
    db.collection('pending_queries').document(query_id).set({
        'liga': liga, 'idioma': idioma, 'pais': pais,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'status': 'pending'
    })
    return JSONResponse(content={{'query_id': query_id, 'status': 'pending', 'message': 'Connect to /ws/live/{{query_id}} for updates'}})

@app.websocket("/ws/live/{query_id}")
async def websocket_endpoint(websocket: WebSocket, query_id: str):
    await websocket.accept()
    ws_connections[query_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections.pop(query_id, None)

@app.get("/refresh_token")
async def refresh_token(stream_id: int = Query(0), league: str = Query(None)):
    proxies = get_proxies()
    streams = scrape_streams("dummy event", league, proxies=proxies)
    new_url = streams[stream_id % len(streams)]['url'] if streams else "No token available"
    return new_url

async def batch_process():
    pending = db.collection('pending_queries').where('status', '==', 'pending').limit(10).stream()
    for doc in pending:
        query_id = doc.id
        data = doc.to_dict()
        filtered = filter_agenda(data['liga'], data['idioma'], data['pais'])
        for event in filtered:
            await process_ai_summary(event)
            event['player_html'] = generate_player_html(event)
        key = f"agenda:{{data['liga'] or ''}}:{{data['idioma'] or ''}}:{{data['pais'] or ''}}"
        r.set(key, json.dumps(filtered), ex=900)
        db.collection('pending_queries').document(query_id).update({{'status': 'processed'}})
        if query_id in ws_connections:
            await ws_connections[query_id].send_text(json.dumps({{'status': 'ready', 'data': filtered}}))
    print("Batch processed")

scheduler.add_job(run_scraper, 'interval', minutes=15)
scheduler.add_job(lambda: asyncio.create_task(batch_process()), 'interval', minutes=5)
scheduler.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
