import os
import random
import requests
import feedparser
import re
import json
import google.generativeai as genai

# === НАСТРОЙКИ ===
MODEL_NAME = 'gemini-2.0-flash' 
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHANNEL = os.environ.get("TG_CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

RSS_FEEDS = [
    "https://forklog.com/feed",
    "https://habr.com/ru/rss/news/?fl=ru",
    "https://ru.beincrypto.com/news/feed/"
]

def load_posted_links():
    if os.path.exists("posted_links.txt"):
        with open("posted_links.txt", "r") as f:
            return set(f.read().splitlines())
    return set()

def save_posted_link(link):
    with open("posted_links.txt", "a") as f:
        f.write(link + "\n")

def generate_post(news_title, news_text):
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Промпт экспертного уровня
    prompt = f"""
    Ты — профессиональный крипто-журналист и тех-аналитик канала "КриптоДзен | Tech & News".
    Твоя задача: превратить новость в захватывающий лонгрид.
    
    Новость: {news_title}
    Детали: {news_text}
    
    Твоя структура поста:
    1. Громкий заголовок (не используй теги, просто текст).
    2. Вступление: захвати внимание читателя.
    3. Суть: подробно, но понятно (2-3 абзаца).
    4. Аналитический взгляд: что это значит для индустрии/рынка?
    5. Вывод/Итог.
    
    ТРЕБОВАНИЯ К ФОРМАТУ:
    - Текст должен быть информативным, глубоким (не поверхностным).
    - БЕЗ HTML-тегов в тексте (я добавлю их сам в коде).
    - В конце добавь список хештегов (например: #Крипто #Tech #Новости #Blockchain).
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

def send_telegram(ai_text, title, image_url, news_link):
    # Разделяем заголовок и текст
    lines = ai_text.split('\n')
    header = f"<b>🚀 {title.upper()}</b>"
    body = "\n".join(lines[1:]) # Все остальное после заголовка
    
    # Формируем красивый HTML
    full_post = f"{header}\n\n{body}"
    
    reply_markup = {"inline_keyboard": [[{"text": "🔗 Читать оригинал", "url": news_link}]]}
    payload = {
        "chat_id": TG_CHANNEL,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }

    if image_url:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        payload.update({"photo": image_url, "caption": full_post[:1024]})
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload.update({"text": full_post[:4096], "disable_web_page_preview": False})
    
    res = requests.post(url, data=payload)
    print(res.json())

if __name__ == "__main__":
    posted_links = load_posted_links()
    source = random.choice(RSS_FEEDS)
    feed = feedparser.parse(source)
    new_entries = [e for e in feed.entries if e.link not in posted_links]
    
    if new_entries:
        item = new_entries[0]
        print(f"Публикуем: {item.title}")
        
        img = None
        if 'media_content' in item: img = item.media_content[0]['url']
        
        raw_desc = re.sub(r'<[^>]+>', '', item.get('description', ''))
        # Передаем подробную информацию для генерации
        ai_text = generate_post(item.title, raw_desc)
        
        send_telegram(ai_text, item.title, img, item.link)
        save_posted_link(item.link)
