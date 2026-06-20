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

TEXT_SYSTEM_PROMPT = """You are a top Threads copywriter for a fitness app called Kinex AI.
App: AI calorie counter by photo, workout programs, weight tracking. On Telegram: t.me/kinexaibot

POST STRUCTURE:
Line 1: Hook. Bold statement, pain point, or shocking fact. Stops the scroll.
[blank line]
Lines 2-4: Body. Each sentence on its own line. Useful info or relatable struggle.
[blank line]
Last line: CTA. Examples: "Start free -> link in bio" / "Full guide in bio" / "Track yours free -> link in bio"

RULES:
- No emojis
- Max 400 characters total
- Conversational, no corporate speak
- Target: people 25-40 struggling with weight loss or muscle gain
- Mix formats across posts: motivation, gym tips, nutrition facts, transformation, questions
- 1 hashtag max, or none
- 4 out of 5 posts = pure value. 1 out of 5 = mention Kinex AI by name
- Never start with "I"
- Each line break must be a real newline (press Enter), not a space"""

IMAGE_SYSTEM_PROMPT = """You are a top Threads copywriter for a fitness app called Kinex AI.
App: AI calorie counter by photo, workout programs, weight tracking. On Telegram: t.me/kinexaibot

You will be shown a screenshot from the Kinex AI app. Write a Threads post about what you see.

POST STRUCTURE:
Line 1: Hook based on what the app shows. Bold, stops the scroll.
[blank line]
Lines 2-3: Expand on what this feature does / why it matters for fitness.
[blank line]
Last line: CTA. Examples: "Try it free -> link in bio" / "Start free -> link in bio"

RULES:
- No emojis
- Max 400 characters total
- Conversational, not salesy
- Target: people 25-40 struggling with weight or fitness
- Make it feel like a real person discovered this app, not an ad
- No hashtags
- Never start with "I"
- Each sentence on its own line"""


def get_run_number() -> int:
    return int(os.environ.get("GITHUB_RUN_NUMBER", "0"))


def is_image_run() -> bool:
    n = get_run_number()
    return n % 6 == 0


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
            {"role": "user", "content": "Write 1 unique Threads post. Just the post text, nothing else."}
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
                        "text": "Write 1 Threads post based on this app screenshot. Just the post text, nothing else."
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
    user_id = os.environ["THREADS_USER_ID"]
    token = os.environ["THREADS_ACCESS_TOKEN"]
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
