import httpx
import os
import base64
import re
from bs4 import BeautifulSoup


async def search_tineye(image_path: str) -> list:
    """
    TinEye reverse image search — free scraping approach.
    API key ki zaroorat nahi.
    """
    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://tineye.com/",
            }
        ) as client:

            # Step 1: freeimage.host pe upload
            upload_resp = await client.post(
                "https://freeimage.host/api/1/upload",
                data={
                    "key": "6d207e02198a847aa98d0a2a901485a5",
                    "action": "upload",
                    "source": img_b64,
                    "format": "json"
                }
            )

            if upload_resp.status_code != 200:
                print("❌ TinEye: image upload failed")
                return []

            img_url = upload_resp.json().get("image", {}).get("url", "")
            if not img_url:
                print("❌ TinEye: image URL nahi mili")
                return []

            print(f"🟠 TinEye image uploaded: {img_url}")

            # Step 2: TinEye URL search
            tineye_url = f"https://tineye.com/search?url={img_url}&sort=score&order=desc"
            resp = await client.get(tineye_url)
            print(f"🟠 TinEye status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"❌ TinEye error: {resp.status_code}")
                return []

            results = parse_tineye_html(resp.text)

            # Fallback: upload direct POST try karo
            if not results:
                results = await tineye_upload_post(client, img_bytes)

            print(f"🟠 TinEye: {len(results)} results found")
            return results

    except Exception as e:
        print(f"❌ TinEye search failed: {e}")
        return []


async def tineye_upload_post(client, img_bytes: bytes) -> list:
    """TinEye pe direct file upload karke search karo."""
    try:
        resp = await client.post(
            "https://tineye.com/search",
            files={"image": ("image.jpg", img_bytes, "image/jpeg")},
            params={"sort": "score", "order": "desc"}
        )
        if resp.status_code == 200:
            return parse_tineye_html(resp.text)
    except Exception as e:
        print(f"⚠️ TinEye upload fallback failed: {e}")
    return []


def parse_tineye_html(html: str) -> list:
    results = []
    seen = set()

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Method 1: TinEye result cards
        for item in soup.select(".match, .result-item, .matches li"):
            link = item.find("a", href=True)
            img  = item.find("img", src=True)
            if link:
                url = link["href"]
                if url.startswith("http") and "tineye.com" not in url:
                    if url not in seen:
                        seen.add(url)
                        results.append({
                            "engine":   "TinEye",
                            "url":      url,
                            "img_url":  img["src"] if img else "",
                            "page_url": url
                        })

        # Method 2: JSON data in page
        if not results:
            json_urls = re.findall(
                r'"backlink"\s*:\s*"(https?://(?!tineye\.com)[^"]{10,})"', html
            )
            img_urls = re.findall(
                r'"image_url"\s*:\s*"(https?://[^"]+)"', html
            )
            for i, url in enumerate(json_urls[:10]):
                if url not in seen:
                    seen.add(url)
                    results.append({
                        "engine":   "TinEye",
                        "url":      url,
                        "img_url":  img_urls[i] if i < len(img_urls) else "",
                        "page_url": url
                    })

        # No results page check
        if not results:
            if "0 results" in html or "No results" in html or "no matches" in html.lower():
                print("🟠 TinEye: No matches found in database")
            else:
                print("🟠 TinEye: Could not parse results")

    except Exception as e:
        print(f"❌ TinEye parse error: {e}")

    return results[:10]