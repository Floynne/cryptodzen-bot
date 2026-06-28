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

# Проверка ключей
if not GEMINI_API_KEY:
    raise ValueError("ОШИБКА: Переменная GEMINI_API_KEY не задана!")

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
    """Генерирует пост как экспертный аналитик"""
    model = genai.GenerativeModel(MODEL_NAME)
    
    prompt = f"""
    Ты — топовый эксперт канала "КриптоДзен | Tech & News".
    Твоя задача: написать вовлекающий пост по новости.
    Заголовок: {news_title}
    Детали: {news_text}
    
    Твоя структура:
    1. Захватывающий заголовок (без тегов).
    2. Основная мысль (3-4 предложения).
    3. Аналитический взгляд: почему это важно для рынка?
    4. Итог (один вывод).
    
    ВАЖНО:
    - Пиши ТОЛЬКО текст. 
    - БЕЗ HTML-тегов, БЕЗ **звездочек**, БЕЗ #решеток внутри текста.
    - В самом конце добавь 2-3 хештега.
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

def send_telegram(clean_text, title, image_url, news_link):
    """Формирует пост и отправляет в ТГ"""
    # Добавляем жирный заголовок в коде Python
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
        payload.update({"photo": image_url, "caption": full_post[:1024]})
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload.update({"text": full_post[:4096], "disable_web_page_preview": False})
    
    res = requests.post(url, data=payload)
    result = res.json()
    
    if result.get("ok"):
        print("✅ ПОСТ ОПУБЛИКОВАН!")
    else:
        print(f"❌ ОШИБКА TELEGRAM: {result}")

if __name__ == "__main__":
    print(f"--- ЗАПУСК (Модель: {MODEL_NAME}) ---")
    posted_links = load_posted_links()
    
    # Выбираем случайную ленту
    source = random.choice(RSS_FEEDS)
    feed = feedparser.parse(source)
    
    # Берем только новые новости
    new_entries = [e for e in feed.entries if e.link not in posted_links]
    
    if new_entries:
        item = new_entries[0] # Самая свежая
        print(f"Новость: {item.title}")
        
        img = None
        if 'media_content' in item: img = item.media_content[0]['url']
        
        # Чистим текст от HTML перед отправкой в ИИ
        raw_desc = re.sub(r'<[^>]+>', '', item.get('description', ''))
        
        ai_text = generate_post(item.title, raw_desc)
        send_telegram(ai_text, item.title, img, item.link)
        
        save_posted_link(item.link)
        print("--- УСПЕШНО ---")
    else:
        print("Нет новых новостей для публикации.")
