import os
import sys
import time
import requests
from openai import OpenAI

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

GITHUB_REPO = "Alex-27-code/threads-bot"
BRANCH = "main"

IMAGES = [
    "photo_1_2026-06-20_10-41-15.jpg",
    "photo_2_2026-06-20_10-41-15.jpg",
    "photo_3_2026-06-20_10-41-15.jpg",
    "photo_4_2026-06-20_10-41-15.jpg",
    "photo_5_2026-06-20_10-41-15.jpg",
    "photo_6_2026-06-20_10-41-15.jpg",
    "photo_7_2026-06-20_10-41-15.jpg",
    "photo_8_2026-06-20_10-41-15.jpg",
    "photo_9_2026-06-20_10-41-15.jpg",
    "photo_10_2026-06-20_10-41-15.jpg",
]

TEXT_SYSTEM_PROMPT = """Ты вирусный копирайтер для Threads. Пишешь для фитнес-приложения Kinex AI.
Приложение: AI-счётчик калорий по фото, программы тренировок, трекер веса. Telegram: t.me/kinexaibot

ЧЕРЕДУЙ эти 4 формата случайно:

ФОРМАТ А — Короткий удар (лучший охват):
Одно смелое предложение. Максимум одна следующая строка. Заканчивай вопросом ИЛИ мягким CTA.
Максимум 100 символов. Никакого балласта.

ФОРМАТ Б — Пост с инсайтом:
Хук (максимум 1 эмодзи, только если реально добавляет удар).
[пустая строка]
2-3 предложения — без пустых строк между ними, только переносы.
[пустая строка]
CTA или вопрос.

ФОРМАТ В — Вопрос к аудитории:
Смелый вопрос как хук.
[пустая строка]
Короткое объяснение почему это важно (1-2 строки).
[пустая строка]
"Пиши в комментах" или похожее.

ФОРМАТ Г — Факт с цифрой:
Статистика в хуке ("67% людей...", "Минус 0.5 кг/неделю означает...").
[пустая строка]
Что это значит на практике.
[пустая строка]
CTA.

ПРАВИЛА:
- Максимум 400 символов
- Максимум 1 эмодзи, только в хуке, только если реально усиливает — чаще без него
- Разговорный стиль, конкретика, никакой воды
- Реальные цифры и детали
- Аудитория: 25-40 лет, хотят похудеть или набрать мышцы
- 4 из 5 постов — чистая польза. 1 из 5 — упомяни Kinex AI
- Никогда не начинай с "Я"
- Без официоза, без "путь к себе", без "трансформируй жизнь"
- Пиши только на русском
- Длина разная: иногда 2 строки лучше чем 5"""

IMAGE_SYSTEM_PROMPT = """Ты вирусный копирайтер для Threads. Пишешь для фитнес-приложения Kinex AI.
Приложение: AI-счётчик калорий по фото, программы тренировок, трекер веса. Telegram: t.me/kinexaibot

Тебе покажут скриншот из приложения Kinex AI. Напиши пост про то что видишь.

Хук на основе скриншота — конкретный, заставляет остановиться.
[пустая строка]
2 строки что делает эта функция и зачем.
[пустая строка]
CTA: "Попробуй бесплатно -> ссылка в bio"

ПРАВИЛА:
- Максимум 1 эмодзи только в хуке
- Максимум 400 символов
- Пиши как реальный пользователь который нашёл это, не как реклама
- Без хэштегов
- Никогда не начинай с "Я"
- Только на русском"""


def get_run_number() -> int:
    return int(os.environ.get("GITHUB_RUN_NUMBER", "0"))


def is_image_run() -> bool:
    n = get_run_number()
    return n % 6 == 1


def pick_image() -> str:
    n = get_run_number()
    idx = (n // 6) % len(IMAGES)
    return IMAGES[idx]


def image_url(filename: str) -> str:
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/images/{filename}"


def generate_text_post(client: OpenAI) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[
            {"role": "system", "content": TEXT_SYSTEM_PROMPT},
            {"role": "user", "content": "Напиши 1 уникальный пост для Threads. Только текст поста, ничего лишнего."}
        ]
    )
    return response.choices[0].message.content.strip()


def generate_image_post(client: OpenAI, img_url: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[
            {"role": "system", "content": IMAGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": img_url}
                    },
                    {
                        "type": "text",
                        "text": "Напиши 1 пост для Threads на основе этого скриншота приложения. Только текст поста, ничего лишнего."
                    }
                ]
            }
        ]
    )
    return response.choices[0].message.content.strip()


def clean_text(text: str) -> str:
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('—', '-').replace('–', '-')
    text = text.replace('…', '...')
    if len(text) > 480:
        text = text[:477] + "..."
    return text


def post_text_only(text: str, user_id: str, token: str, base: str) -> str:
    r = requests.post(
        f"{base}/{user_id}/threads",
        data={"media_type": "TEXT", "text": text, "access_token": token},
        timeout=30
    )
    print(f"Create: {r.status_code} | {r.text[:200]}")
    r.raise_for_status()
    return r.json()["id"]


def post_with_image(text: str, img_url: str, user_id: str, token: str, base: str) -> str:
    r = requests.post(
        f"{base}/{user_id}/threads",
        data={
            "media_type": "IMAGE",
            "image_url": img_url,
            "text": text,
            "access_token": token
        },
        timeout=30
    )
    print(f"Create (image): {r.status_code} | {r.text[:200]}")
    r.raise_for_status()
    return r.json()["id"]


def publish(container_id: str, user_id: str, token: str, base: str) -> str:
    time.sleep(5)
    r = requests.post(
        f"{base}/{user_id}/threads_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30
    )
    print(f"Publish: {r.status_code} | {r.text[:200]}")
    r.raise_for_status()
    return r.json()["id"]


if __name__ == "__main__":
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    user_id = os.environ["THREADS_USER_ID_RU"]
    token = os.environ["THREADS_ACCESS_TOKEN_RU"]
    base = "https://graph.threads.net/v1.0"

    run_n = get_run_number()
    use_image = is_image_run()

    print(f"Run #{run_n} | image_post={use_image}")

    if use_image:
        filename = pick_image()
        img_url = image_url(filename)
        print(f"Image: {filename}")
        text = generate_image_post(client, img_url)
        text = clean_text(text)
        print(f"Post ({len(text)} chars):\n{text}")
        container_id = post_with_image(text, img_url, user_id, token, base)
    else:
        text = generate_text_post(client)
        text = clean_text(text)
        print(f"Post ({len(text)} chars):\n{text}")
        container_id = post_text_only(text, user_id, token, base)

    thread_id = publish(container_id, user_id, token, base)
    print(f"Published! Thread ID: {thread_id}")
