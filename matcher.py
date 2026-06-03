import httpx
import asyncio
import os
import tempfile
import numpy as np
import cv2
from deepface import DeepFace
from bs4 import BeautifulSoup
import re


def crop_face_only(image_path: str):
    try:
        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend="opencv",
            enforce_detection=True,
            align=True
        )

        if not faces:
            return None

        best = max(faces, key=lambda x: x.get("confidence", 0))
        face_confidence = best.get("confidence", 0)

        if face_confidence < 0.3:
            return None

        face_array = best["face"]
        face_img = (face_array * 255).astype(np.uint8)
        face_bgr = cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        cv2.imwrite(tmp.name, face_bgr)
        return tmp.name

    except Exception:
        return None


async def extract_images_from_page(client, page_url: str) -> list:
    try:
        response = await client.get(page_url, timeout=10)
        if response.status_code != 200:
            return []

        content_type = response.headers.get("content-type", "")

        if "image" in content_type:
            return [page_url]

        soup = BeautifulSoup(response.text, "html.parser")
        images = []

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            images.append(og_image["content"])

        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            images.append(twitter_image["content"])

        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(page_url)
                src = f"{parsed.scheme}://{parsed.netloc}{src}"
            if src.startswith("http"):
                images.append(src)

        for script in soup.find_all("script", type="application/ld+json"):
            text = script.string or ""
            urls = re.findall(r'"image":\s*"(https?://[^"]+)"', text)
            images.extend(urls)

        seen = set()
        unique = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique.append(img)

        return unique[:5]

    except Exception:
        return []


async def compare_face(client, original_path, img_url, engine, page_url, result):
    orig_face  = None
    found_face = None
    tmp_path   = None

    try:
        response = await client.get(img_url, timeout=10)
        if response.status_code != 200:
            return None

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            return None

        suffix = ".png" if "png" in content_type else ".jpg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        orig_face  = crop_face_only(original_path)
        found_face = crop_face_only(tmp_path)

        if orig_face is None or found_face is None:
            return None

        result_verify = DeepFace.verify(
            img1_path=orig_face,
            img2_path=found_face,
            model_name="Facenet512",
            enforce_detection=False,
            distance_metric="cosine",
            align=True
        )

        distance   = result_verify.get("distance", 1.0)
        verified   = result_verify.get("verified", False)
        confidence = max(0, int((1 - distance) * 100))

        print(f"🔎 {engine} | dist={distance:.3f} | conf={confidence}% | verified={verified} | {page_url[:50]}")

        if verified or confidence >= 60:
            risk = "HIGH" if confidence >= 85 else "MEDIUM" if confidence >= 65 else "LOW"
            print(f"✅ Match! {engine} — {confidence}% — {page_url[:50]}")
            return {
                "engine":     engine,
                "url":        page_url,
                "image_url":  img_url,
                "confidence": confidence,
                "risk":       risk,
                "title":      result.get("title", ""),
                "thumbnail":  img_url
            }
        else:
            print(f"❌ No match: {engine} — {confidence}%")
            return None

    except Exception:
        return None

    finally:
        for p in [tmp_path, orig_face, found_face]:
            if p and p != original_path:
                try:
                    os.unlink(p)
                except:
                    pass


async def check_single_match(client, original_path: str, result: dict):
    url        = result.get("url", "")
    engine     = result.get("engine", "Unknown")
    direct_img = result.get("img_url", "") or result.get("thumbnail", "")

    if not url or url == "N/A":
        return None

    try:
        image_urls = []

        # Priority 1: Result mein already img_url hai to pehle use karo
        if direct_img and direct_img.startswith("http"):
            image_urls.append(direct_img)

        # Priority 2: Page se images extract karo
        page_images = await extract_images_from_page(client, url)
        for img in page_images:
            if img not in image_urls:
                image_urls.append(img)

        if not image_urls:
            return None

        matches = []
        for img_url in image_urls[:6]:
            match = await compare_face(client, original_path, img_url, engine, url, result)
            if match:
                matches.append(match)
                break  # Pehla match mila — done

        return matches if matches else None

    except Exception:
        return None


async def match_faces(original_path: str, original_embedding: list, search_results: list) -> list:
    matched          = []
    results_to_check = search_results[:20]

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    ) as client:
        tasks = [
            check_single_match(client, original_path, result)
            for result in results_to_check
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"⚠️ gather exception: {str(result)[:60]}")
                continue
            if isinstance(result, list):
                matched.extend(result)
            elif isinstance(result, dict) and result.get("confidence", 0) > 0:
                matched.append(result)

    matched.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return matched