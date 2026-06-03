import os
import httpx
import base64
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def describe_face_groq(image_path: str) -> str:
    """Use Groq LLaVA to describe face in image"""
    if not GROQ_API_KEY:
        print("⚠️ Groq API key nahi hai — skipping")
        return None

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = image_path.lower().split(".")[-1]
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Describe this person's face: gender, approximate age, hair color, skin tone, distinctive features. 1-2 sentences only."
                        }
                    ]
                }
            ],
            "max_tokens": 150,
            "temperature": 0.1
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, json=payload)
            print(f"🟢 Groq status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                print(f"🟢 Groq face description: {text[:80]}...")
                return text
            else:
                err = response.json().get("error", {}).get("message", "unknown")
                print(f"⚠️ Groq error: {err[:100]}")
                return None

    except Exception as e:
        print(f"⚠️ Groq exception: {str(e)[:80]}")
        return None


async def search_google(image_path: str) -> list:
    """Use Groq to describe face — replaces Google/Gemini"""
    description = await describe_face_groq(image_path)
    if not description:
        return []

    return [{
        "engine": "Groq AI",
        "url": "N/A",
        "thumbnail": "",
        "title": f"Face Analysis: {description}"
    }]