import os
import random
import requests
import feedparser
import re
import json
import google.generativeai as genai

# Настройки
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
    if 'media_content' in entry:
        for media in entry.media_content:
            if 'url' in media: return media['url']
    if 'enclosures' in entry:
        for enc in entry.enclosures:
            if 'href' in enc: return enc['href']
    content = entry.get('description', '') + str(entry.get('content', ''))
    match = re.search(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']', content, re.IGNORECASE)
    return match.group(1) if match else None

def generate_post(news_text):
    # Пытаемся использовать Flash, если нет - Pro
    model_name = 'gemini-2.5-flash' 
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    Ты — ИИ-автор канала "КриптоДзен | Tech & News". 
    Твоя задача: превратить скучную новость в захватывающий пост.
    Новость: {news_text}
    
    Правила:
    1. Сделай КРУТОЙ заголовок (используй <b>текст</b>).
    2. Напиши суть новости в 3-4 предложениях.
    3. Используй эмодзи.
    4. В конце добавь 2-3 хештега.
    5. Используй ТОЛЬКО HTML (<b>, <i>). Не используй символы ** или # для заголовков.
    6. Не пиши ничего, кроме самого текста поста.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Ошибка модели {model_name}, пробуем запасную...")
        model = genai.GenerativeModel('gemini-pro') # Запасной вариант
        response = model.generate_content(prompt)
        return response.text.strip()

def send_telegram(post_html, image_url, news_link):
    reply_markup = {"inline_keyboard": [[{"text": "🔗 Читать источник", "url": news_link}]]}
    
    # Очистка текста от лишних символов, которые могут ломать HTML Telegram
    post_html = post_html.replace('**', '').replace('`', '')

    if image_url:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        data = {
            "chat_id": TG_CHANNEL,
            "photo": image_url,
            "caption": post_html[:1024], # Лимит Telegram для подписей
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        }
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {
            "chat_id": TG_CHANNEL,
            "text": post_html[:4096],
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup),
            "disable_web_page_preview": True
        }
    
    res = requests.post(url, data=data)
    print("Результат отправки:", res.json())

if __name__ == "__main__":
    feed = feedparser.parse(random.choice(RSS_FEEDS))
    if feed.entries:
        item = random.choice(feed.entries[:5])
        img = extract_image(item)
        text = f"{item.title}. {item.description}"
        # Очистка от HTML тегов перед генерацией
        text = re.sub(r'<[^>]+>', '', text)
        
        print("Генерируем контент...")
        final_post = generate_post(text)
        send_telegram(final_post, img, item.link)
