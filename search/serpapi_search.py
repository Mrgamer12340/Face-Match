import os
import httpx
import base64
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

async def search_serpapi(image_path: str) -> list:
    """Google Lens reverse image search via SerpApi"""
    if not SERPAPI_KEY:
        print("⚠️ SerpApi key nahi hai — skipping")
        return []

    results = []

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        image_b64 = base64.b64encode(image_data).decode("utf-8")

        async with httpx.AsyncClient(timeout=30) as client:

            # Step 1: Upload image to freeimage.host (no key needed)
            upload_resp = await client.post(
                "https://freeimage.host/api/1/upload",
                data={
                    "key": "6d207e02198a847aa98d0a2a901485a5",
                    "action": "upload",
                    "source": image_b64,
                    "format": "json"
                }
            )

            image_url = None
            if upload_resp.status_code == 200:
                data = upload_resp.json()
                image_url = data.get("image", {}).get("url", "")
                print(f"🟡 Image uploaded: {image_url}")

            if not image_url:
                print("⚠️ Image upload failed — SerpApi skipping")
                return []

            # Step 2: Google Lens search
            search_resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_lens",
                    "url": image_url,
                    "api_key": SERPAPI_KEY
                },
                timeout=30
            )

            print(f"🟡 SerpApi status: {search_resp.status_code}")

            if search_resp.status_code == 200:
                data = search_resp.json()

                # Visual matches
                visual_matches = data.get("visual_matches", [])
                for match in visual_matches[:15]:
                    url = match.get("link", "")
                    if url:
                        results.append({
                            "engine": "Google Lens",
                            "url": url,
                            "thumbnail": match.get("thumbnail", ""),
                            "title": match.get("title", "")
                        })

                # Knowledge graph (person info)
                knowledge = data.get("knowledge_graph", {})
                if knowledge.get("title"):
                    print(f"🟡 Person identified: {knowledge.get('title')}")
                    results.append({
                        "engine": "Google Lens",
                        "url": knowledge.get("website", "N/A"),
                        "thumbnail": knowledge.get("image", ""),
                        "title": f"Identity: {knowledge.get('title')}"
                    })

                print(f"🟡 SerpApi Google Lens: {len(results)} results found")

            else:
                err = search_resp.json().get("error", "unknown")
                print(f"⚠️ SerpApi error: {err}")

    except Exception as e:
        print(f"⚠️ SerpApi exception: {str(e)[:100]}")

    return results