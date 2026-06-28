import os
import random
import requests
import feedparser
import re
import json
import google.generativeai as genai

# Конфигурация
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHANNEL = os.environ.get("TG_CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

RSS_FEEDS = [
    "https://forklog.com/feed",
    "https://habr.com/ru/rss/news/?fl=ru",
    "https://ru.beincrypto.com/news/feed/"
]

def clean_html(text):
    """Полная очистка текста от грехов ИИ и лишних тегов"""
    text = text.replace('**', '') # ИИ обожает ставить звездочки, убираем
    text = text.replace('`', '')
    # Убираем все теги, кроме разрешенных b, i
    text = re.sub(r'<(?!/?(b|i)\b)[^>]+>', '', text)
    return text

def extract_image(entry):
    """Поиск картинки в разных полях новости"""
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

def generate_post(news_text):
    """Генерация текста через ИИ"""
    # Используем модель gemini-1.5-flash (самая стабильная сейчас)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Ты — топовый редактор канала "КриптоДзен | Tech & News". 
    Перепиши эту новость: {news_text}
    
    Требования:
    1. Начни с жирного заголовка: <b>ЗАГОЛОВОК</b>
    2. Кратко и хайпово расскажи суть (3-5 предложений).
    3. Используй эмодзи.
    4. В конце добавь хештеги.
    5. Используй ТОЛЬКО HTML теги <b> и <i>. Никаких звездочек!
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

def send_telegram(post_html, image_url, news_link):
    """Отправка в Telegram"""
    reply_markup = {"inline_keyboard": [[{"text": "🔗 Читать оригинал", "url": news_link}]]}
    post_html = clean_html(post_html)

    if image_url:
        print(f"Отправляем фото: {image_url}")
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        data = {
            "chat_id": TG_CHANNEL,
            "photo": image_url,
            "caption": post_html[:1024],
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        }
    else:
        print("Картинка не найдена, отправляем только текст...")
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {
            "chat_id": TG_CHANNEL,
            "text": post_html[:4096],
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup),
            "disable_web_page_preview": True
        }
    
    res = requests.post(url, data=data)
    result = res.json()
    if result.get("ok"):
        print("✅ ПОСТ УСПЕШНО ОТПРАВЛЕН!")
    else:
        print(f"❌ ОШИБКА TELEGRAM: {result}")

if __name__ == "__main__":
    print("--- ЗАПУСК БОТА ---")
    url = random.choice(RSS_FEEDS)
    print(f"Читаем ленту: {url}")
    feed = feedparser.parse(url)
    
    if feed.entries:
        item = random.choice(feed.entries[:5])
        print(f"Выбрана новость: {item.title}")
        
        img = extract_image(item)
        raw_text = f"{item.title}. {item.get('description', '')}"
        raw_text = re.sub(r'<[^>]+>', '', raw_text) # чистим от мусора перед ИИ
        
        print("Запрос к ИИ...")
        try:
            final_post = generate_post(raw_text)
            print("Текст сгенерирован!")
            send_telegram(final_post, img, item.link)
        except Exception as e:
            print(f"❌ Ошибка ИИ: {e}")
    else:
        print("❌ Не удалось получить новости (лента пуста).")
    print("--- РАБОТА ЗАВЕРШЕНА ---")
