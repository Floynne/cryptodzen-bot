import os
import random
import requests
import feedparser
import google.generativeai as genai

# Достаем ключи из секретов GitHub
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHANNEL = os.environ.get("TG_CHANNEL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Сайты, откуда бот будет брать свежие новости
RSS_FEEDS = [
    "https://forklog.com/feed", # Крипта
    "https://habr.com/ru/rss/news/?fl=ru", # IT Новости
    "https://ru.beincrypto.com/news/feed/" # Крипта
]

def get_news():
    feed_url = random.choice(RSS_FEEDS)
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return None
    # Берем одну случайную новость из 5 самых свежих
    entry = random.choice(feed.entries[:5])
    return f"{entry.title}. {entry.description}"

def generate_post(news_text):
    # Используем бесплатную и быструю модель
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Ты автор крутого Telegram-канала "КриптоДзен | Tech & News".
    Вот свежая новость: {news_text}
    
    Перепиши её для своего канала. 
    - Сделай текст интересным, современным и понятным.
    - Добавь подходящие эмодзи.
    - Объем: около 500-700 символов.
    - В конце добавь хештеги (например, #Крипта #Tech).
    - Пиши обычным текстом, категорически НЕ используй звездочки (**) и жирный шрифт, чтобы Telegram не выдал ошибку.
    - Выдай только готовый пост для публикации.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHANNEL,
        "text": text
    }
    response = requests.post(url, data=payload)
    print("Ответ Telegram:", response.text)

if __name__ == "__main__":
    try:
        news = get_news()
        if news:
            print("Новость найдена, генерируем пост...")
            post = generate_post(news)
            send_telegram(post)
            print("Успех! Пост опубликован.")
        else:
            print("Не удалось получить новости.")
    except Exception as e:
        print(f"Ошибка: {e}")
