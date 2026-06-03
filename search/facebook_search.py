import httpx
import os
from dotenv import load_dotenv

load_dotenv()

FACEBOOK_API_KEY = os.getenv("FACEBOOK_API_KEY", "")

async def search_facebook(image_path: str, face_description: str = "") -> list:
    """
    Facebook People Search via RapidAPI (Facebook Scraper3).
    Profile pic URL directly matcher ko bhejte hain — agar accessible hai to match hoga.
    Returns: list of { engine, url, img_url, page_url, title }
    """
    if not FACEBOOK_API_KEY:
        print("⚠️ Facebook API key nahi hai — skipping")
        return []

    if not face_description:
        print("⚠️ Face description nahi hai — Facebook skipping")
        return []

    query = extract_search_query(face_description)
    print(f"🔵 Facebook search query: {query}")

    results = []

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://facebook-scraper3.p.rapidapi.com/search/people",
                headers={
                    "X-RapidAPI-Key": FACEBOOK_API_KEY,
                    "X-RapidAPI-Host": "facebook-scraper3.p.rapidapi.com",
                },
                params={"query": query, "count": "10"}
            )

            print(f"🔵 Facebook status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"❌ Facebook error: {resp.text[:150]}")
                return []

            data = resp.json()
            people = data.get("results", [])

            for person in people[:10]:
                profile_url = person.get("url", "")
                name        = person.get("name", "")
                profile_pic = person.get("profile_picture", {})
                img_url     = profile_pic.get("url", "") if isinstance(profile_pic, dict) else ""

                if profile_url:
                    results.append({
                        "engine":   "Facebook",
                        "url":      profile_url,
                        "img_url":  img_url,
                        "page_url": profile_url,
                        "title":    name
                    })

            print(f"🔵 Facebook: {len(results)} profiles found")

    except Exception as e:
        print(f"❌ Facebook search failed: {e}")

    return results


def extract_search_query(description: str) -> str:
    """Groq description se search query banao."""
    desc_lower = description.lower()

    # Gender
    if any(w in desc_lower for w in ["female", "woman", "girl", "lady"]):
        gender = "woman"
    else:
        gender = "man"

    # Age
    age = ""
    if any(w in desc_lower for w in ["20s", "twenties", "young adult"]):
        age = "20s"
    elif any(w in desc_lower for w in ["30s", "thirties"]):
        age = "30s"
    elif any(w in desc_lower for w in ["40s", "forties"]):
        age = "40s"
    elif any(w in desc_lower for w in ["50s", "fifties", "60s", "sixties", "70s", "senior", "elderly"]):
        age = "50s"

    # Hair color
    hair = ""
    for color in ["brown hair", "black hair", "blonde hair", "red hair", "gray hair", "white hair", "dark hair"]:
        if color in desc_lower:
            hair = color
            break

    parts = [p for p in [gender, age, hair] if p]
    return " ".join(parts) if parts else gender