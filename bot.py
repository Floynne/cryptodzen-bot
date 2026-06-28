import os
import random
import requests
import feedparser
import re
import json
import google.generativeai as genai

# Достаем ключи из секретов
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHANNEL = os.environ.get("TG_CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Источники новостей
RSS_FEEDS = [
    "https://forklog.com/feed",
    "https://habr.com/ru/rss/news/?fl=ru",
    "https://ru.beincrypto.com/news/feed/"
]

def extract_image(entry):
    """Пытаемся найти картинку в новости"""
    # Вариант 1: В специальных тегах медиа
    if 'media_content' in entry:
        for media in entry.media_content:
            if 'url' in media and media['url'].startswith('http'):
                return media['url']
    if 'enclosures' in entry:
        for enc in entry.enclosures:
            if 'type' in enc and enc['type'].startswith('image/'):
                return enc['href']
    
    # Вариант 2: Ищем ссылку на картинку прямо в тексте новости
    content = entry.get('description', '')
    if 'content' in entry:
        content += str(entry.content)
    match = re.search(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp))["\']', content, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

def get_news():
    feed_url = random.choice(RSS_FEEDS)
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return None
    
    # Берем случайную из 5 самых свежих
    entry = random.choice(feed.entries[:5])
    
    # Очищаем от лишнего HTML-мусора для ИИ
    clean_desc = re.sub(r'<[^>]+>', '', entry.get('description', ''))
    
    return {
        "text": f"{entry.get('title', '')}. {clean_desc}",
        "link": entry.get('link', ''),
        "image_url": extract_image(entry)
    }

def generate_post(news_text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Ты профессиональный редактор Telegram-канала "КриптоДзен | Tech & News".
    Вот свежая новость: {news_text}
    
    Напиши пост для канала по этим правилам:
    1. Придумай короткий, цепляющий заголовок и оберни его в теги <b>Заголовок</b>.
    2. Сделай краткую выжимку самого интересного из новости (понятным языком).
    3. Лимит текста: СТРОГО до 800 символов (иначе текст не поместится под фото в Telegram).
    4. Используй эмодзи для стиля (но не переборщи).
    5. Форматируй текст ТОЛЬКО базовым HTML: <b>жирный</b>, <i>курсив</i>. Никаких звездочек Markdown (**) и решеток (##) в тексте. Обязательно закрывай теги!
    6. В конце добавь 2-3 хештега (например, #Крипта #TechНовости).
    7. В ответе выдай ТОЛЬКО готовый код поста, без приветствий и твоих комментариев.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def send_telegram(post_html, image_url, news_link):
    # Создаем красивую кнопку (Inline keyboard)
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🔗 Читать оригинал", "url": news_link}]
        ]
    }
    
    # Если картинка нашлась, отправляем пост с фото
    if image_url:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TG_CHANNEL,
            "photo": image_url,
            "caption": post_html,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        }
    # Если картинки нет, отправляем просто текст с кнопкой
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHANNEL,
            "text": post_html,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup),
            "disable_web_page_preview": True
        }
        
    response = requests.post(url, data=payload)
    print("Ответ Telegram:", response.json())

if __name__ == "__main__":
    try:
        news_data = get_news()
        if news_data:
            print("Нашли новость! Генерируем пост...")
            post_text = generate_post(news_data["text"])
            
            print(f"Картинка найдена: {news_data['image_url']}")
            send_telegram(post_text, news_data["image_url"], news_data["link"])
            
            print("Успех! Мега-пост опубликован.")
        else:
            print("Не удалось получить новости.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
