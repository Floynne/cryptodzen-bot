import os
import random
import requests
import feedparser
import re
import json
import google.generativeai as genai

# === НАСТРОЙКИ ===
MODEL_NAME = 'gemini-1.5-flash' # Поставь ту, которая у тебя работает (1.5-flash или 2.0-flash-exp)
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHANNEL = os.environ.get("TG_CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

RSS_FEEDS = [
    "https://forklog.com/feed",
    "https://habr.com/ru/rss/news/?fl=ru",
    "https://ru.beincrypto.com/news/feed/"
]

def extract_image(entry):
    img = None
    if 'media_content' in entry and entry.media_content:
        img = entry.media_content[0]['url']
    elif 'enclosures' in entry and entry.enclosures:
        img = entry.enclosures[0]['href']
    if not img:
        content = entry.get('description', '') + str(entry.get('content', ''))
        match = re.search(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']', content, re.IGNORECASE)
        if match: img = match.group(1)
    return img

def generate_post(news_title, news_text):
    """Генерирует только ТЕКСТ поста без HTML тегов"""
    model = genai.GenerativeModel(MODEL_NAME)
    
    prompt = f"""
    Ты редактор КриптоДзен. Перепиши новость кратко и хайпово.
    Заголовок новости: {news_title}
    Текст: {news_text}
    
    Правила:
    1. Пиши ТОЛЬКО текст поста. 
    2. НЕ используй жирный шрифт, курсив, звездочки или решетки.
    3. Ограничься 3-5 предложениями. 
    4. Добавь подходящие эмодзи и 2-3 хештега в конце.
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

def send_telegram(clean_text, title, image_url, news_link):
    """Формирует HTML и отправляет в TG"""
    
    # Сами формируем правильный HTML. Текст от ИИ вставляем как есть.
    # Очищаем заголовок от возможных спецсимволов HTML
    safe_title = title.replace('<', '&lt;').replace('>', '&gt;')
    
    full_post = f"<b>🔥 {safe_title.upper()}</b>\n\n{clean_text}"
    
    reply_markup = {"inline_keyboard": [[{"text": "🔗 Читать оригинал", "url": news_link}]]}

    payload = {
        "chat_id": TG_CHANNEL,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }

    if image_url:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        payload["photo"] = image_url
        payload["caption"] = full_post[:1024]
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload["text"] = full_post[:4096]
        payload["disable_web_page_preview"] = True
    
    res = requests.post(url, data=payload)
    result = res.json()
    
    if result.get("ok"):
        print("✅ ПОСТ ОПУБЛИКОВАН!")
    else:
        # Если всё же ошибка в HTML, шлем просто текст без тегов
        print(f"Ошибка HTML, шлем plain text. Ошибка: {result.get('description')}")
        payload.pop("parse_mode", None)
        if image_url:
            payload["caption"] = f"{title}\n\n{clean_text}"[:1024]
        else:
            payload["text"] = f"{title}\n\n{clean_text}"[:4096]
        requests.post(url, data=payload)

if __name__ == "__main__":
    print(f"--- СТАРТ (Модель: {MODEL_NAME}) ---")
    try:
        source = random.choice(RSS_FEEDS)
        feed = feedparser.parse(source)
        if feed.entries:
            item = random.choice(feed.entries[:5])
            print(f"Новость: {item.title}")
            
            img = extract_image(item)
            # Чистим описание от HTML-мусора
            raw_description = re.sub(r'<[^>]+>', '', item.get('description', ''))
            
            ai_text = generate_post(item.title, raw_description)
            send_telegram(ai_text, item.title, img, item.link)
        else:
            print("Лента пуста")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
    print("--- КОНЕЦ ---")
