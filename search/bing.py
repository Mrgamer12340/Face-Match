import httpx
import os
import base64
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

async def search_bing(image_path: str) -> list:
    """
    Bing Reverse Image Search — direct scraping.
    RapidAPI endpoint (bing-image-search5) dead tha (503).
    Ab direct Bing use karte hain freeimage.host upload ke baad.
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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        ) as client:

            # Step 1: freeimage.host pe image upload karo
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
                print("❌ Bing: image upload failed")
                return []

            img_url = upload_resp.json().get("image", {}).get("url", "")
            if not img_url:
                print("❌ Bing: image URL nahi mili")
                return []

            print(f"🔷 Bing image uploaded: {img_url}")

            # Step 2: Bing Visual Search direct scrape
            bing_url = f"https://www.bing.com/images/search?view=detailv2&iss=sbi&FORM=IRSBIQ&q=imgurl:{img_url}"
            resp = await client.get(bing_url)
            print(f"🔷 Bing status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"❌ Bing HTTP error: {resp.status_code}")
                return []

            results = parse_bing_html(resp.text)

            # Fallback URL try karo
            if not results:
                bing_url2 = f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{img_url}"
                resp2 = await client.get(bing_url2)
                results = parse_bing_html(resp2.text)

            print(f"🔷 Bing: {len(results)} results found")
            return results

    except Exception as e:
        print(f"❌ Bing search failed: {e}")
        return []


def parse_bing_html(html: str) -> list:
    results = []
    seen = set()

    try:
        # Method 1: JSON purl fields (sabse reliable)
        json_urls = re.findall(
            r'"purl"\s*:\s*"(https?://(?!(?:www\.)?bing\.com)[^"]{15,})"', html
        )
        thumbs = re.findall(r'"turl"\s*:\s*"(https?://[^"]+)"', html)

        for i, url in enumerate(json_urls[:15]):
            if url not in seen:
                seen.add(url)
                results.append({
                    "engine":   "Bing",
                    "url":      url,
                    "img_url":  thumbs[i] if i < len(thumbs) else "",
                    "page_url": url
                })

        # Method 2: HTML card scraping
        if not results:
            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select(".iuscp, .richcap, .b_algo, .dgControl_list li"):
                a = item.find("a", href=True)
                img = item.find("img", src=True)
                if a:
                    url = a["href"]
                    if url.startswith("http") and "bing.com" not in url:
                        if url not in seen:
                            seen.add(url)
                            results.append({
                                "engine":   "Bing",
                                "url":      url,
                                "img_url":  img["src"] if img else "",
                                "page_url": url
                            })

        # Method 3: href fallback
        if not results:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if (href.startswith("http")
                        and "bing.com" not in href
                        and "microsoft.com" not in href
                        and "go.microsoft" not in href):
                    if href not in seen:
                        seen.add(href)
                        results.append({
                            "engine":   "Bing",
                            "url":      href,
                            "img_url":  "",
                            "page_url": href
                        })
                if len(results) >= 15:
                    break

    except Exception as e:
        print(f"❌ Bing parse error: {e}")

    return results[:15]