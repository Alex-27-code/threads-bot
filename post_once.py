import os
import sys
import time
import requests
from openai import OpenAI

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SYSTEM_PROMPT = """You are a top Threads copywriter for a fitness app called Kinex AI.
App features: AI calorie counter by photo, workout programs, weight tracking. Available on Telegram at t.me/kinexaibot

POST STRUCTURE:
1. HOOK (line 1): Bold statement, pain, or shocking fact. Stops the scroll.
2. BODY (2-4 lines): Expand on the hook. Useful info or relatable pain.
3. CTA (last line): Soft call to action. Examples:
   - "How I fixed this -> link in bio"
   - "Full guide in bio"
   - "Start free -> link in bio"

RULES:
- Max 400 characters total
- Conversational, no corporate speak
- Target: people 25-40 struggling with weight loss or building muscle
- Mix formats: pain, education, surprising fact, question, transformation
- 1 hashtag max, or none
- 4 out of 5 posts = pure value. 1 out of 5 = mention Kinex AI by name
- Never start with "I" """


def generate_post() -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Write 1 unique Threads post. Just the post text, nothing else."}
        ]
    )
    return response.choices[0].message.content.strip()


def clean_text(text: str) -> str:
    text = text.replace('’', "'").replace('‘', "'")
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('—', '-').replace('–', '-')
    text = text.replace('…', '...')
    if len(text) > 480:
        text = text[:477] + "..."
    return text


def post_to_threads(text: str) -> str:
    user_id = os.environ["THREADS_USER_ID"]
    token = os.environ["THREADS_ACCESS_TOKEN"]
    base = "https://graph.threads.net/v1.0"
    text = clean_text(text)

    r = requests.post(
        f"{base}/{user_id}/threads",
        data={"media_type": "TEXT", "text": text, "access_token": token},
        timeout=30
    )
    print(f"Create: {r.status_code} | {r.text[:200]}")
    r.raise_for_status()
    container_id = r.json()["id"]

    time.sleep(3)

    r2 = requests.post(
        f"{base}/{user_id}/threads_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30
    )
    print(f"Publish: {r2.status_code} | {r2.text[:200]}")
    r2.raise_for_status()
    return r2.json()["id"]


if __name__ == "__main__":
    print("Generating post...")
    text = generate_post()
    print(f"Post text ({len(text)} chars): {text}")
    thread_id = post_to_threads(text)
    print(f"Published! Thread ID: {thread_id}")
