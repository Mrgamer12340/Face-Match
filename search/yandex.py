import httpx
import re
import tempfile
import os
import numpy as np


def crop_face_for_search(image_path: str) -> str:
    """
    Yandex ko sirf face crop bhejo — poori body nahi.
    Yandex full body se dress/pose match karta hai — face crop se face match karega.
    """
    try:
        from deepface import DeepFace
        import cv2

        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend="opencv",
            enforce_detection=True,
            align=True
        )

        if not faces:
            return image_path

        best = max(faces, key=lambda x: x.get("confidence", 0))

        if best.get("confidence", 0) < 0.5:
            return image_path

        face_array = best["face"]
        face_img   = (face_array * 255).astype(np.uint8)
        face_bgr   = cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR)

        # Thoda zoom out — forehead/chin include karo
        h, w = face_bgr.shape[:2]
        padded = cv2.copyMakeBorder(
            face_bgr,
            int(h * 0.2), int(h * 0.2),
            int(w * 0.1), int(w * 0.1),
            cv2.BORDER_REPLICATE
        )

        resized = cv2.resize(padded, (300, 300))

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        cv2.imwrite(tmp.name, resized, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"✂️ Face cropped for Yandex search: {tmp.name}")
        return tmp.name

    except Exception as e:
        print(f"⚠️ Face crop failed: {e} — sending original")
        return image_path


async def search_yandex(image_path: str) -> list:
    """
    Yandex reverse image search — face crop bhejo, dress nahi.
    Returns: list of { engine, url, img_url, page_url }
    """
    face_path = None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        face_path = crop_face_for_search(image_path)

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=headers
        ) as client:

            with open(face_path, "rb") as f:
                img_bytes = f.read()

            upload_resp = await client.post(
                "https://yandex.com/images/search",
                params={"rpt": "imageview", "format": "json"},
                files={"upfile": ("face.jpg", img_bytes, "image/jpeg")},
                data={"prg": "1"}
            )

            final_url = str(upload_resp.url)
            print(f"🔴 Yandex redirect: {final_url[:100]}")

            results = parse_yandex_html(upload_resp.text)

            # Sites page fallback
            if not results:
                sites_url = re.sub(r'rpt=\w+', 'rpt=sites', final_url)
                if 'rpt=' not in sites_url:
                    sites_url += '&rpt=sites'
                sites_resp = await client.get(sites_url)
                results = parse_yandex_html(sites_resp.text)

            print(f"🔴 Yandex: {len(results)} results found")
            return results

    except Exception as e:
        print(f"❌ Yandex search failed: {e}")
        return []

    finally:
        if face_path and face_path != image_path and os.path.exists(face_path):
            try:
                os.remove(face_path)
            except:
                pass


def parse_yandex_html(html: str) -> list:
    results = []
    seen    = set()

    try:
        page_links = re.findall(
            r'"url"\s*:\s*"(https?://(?!yandex|ya\.ru)[^"]{15,})"', html
        )
        thumb_urls = re.findall(
            r'"thumb"\s*:\s*\{[^}]*"url"\s*:\s*"(//[^"]+|https?://[^"]+)"', html
        )

        for i, link in enumerate(page_links[:8]):
            if link in seen:
                continue
            seen.add(link)
            thumb = thumb_urls[i] if i < len(thumb_urls) else ""
            if thumb.startswith("//"):
                thumb = "https:" + thumb
            results.append({
                "engine":   "Yandex",
                "url":      link,
                "img_url":  thumb,
                "page_url": link
            })

        if not results:
            hrefs = re.findall(
                r'href="(https?://(?!yandex|ya\.ru)[^"]{20,})"', html
            )
            imgs = re.findall(r'<img[^>]+src="(https?://[^"]+)"', html)
            for i, href in enumerate(hrefs[:6]):
                if href in seen:
                    continue
                seen.add(href)
                results.append({
                    "engine":   "Yandex",
                    "url":      href,
                    "img_url":  imgs[i] if i < len(imgs) else "",
                    "page_url": href
                })

    except Exception as e:
        print(f"❌ Yandex parse error: {e}")

    return results