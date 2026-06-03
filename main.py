from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import shutil
import uuid
from face_extract import extract_face
from matcher import match_faces
from search.yandex import search_yandex
from search.groq_search import search_google
from search.bing import search_bing
from search.tineye import search_tineye
from search.serpapi_search import search_serpapi
from search.facebook_search import search_facebook

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"status": "FaceGuard API running ✅"}

@app.post("/scan")
async def scan_face(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Step 1: Extract face
        face_embedding = extract_face(filepath)
        if face_embedding is None:
            return {"error": "Face detect nahi hua — clear photo upload karo"}

        # Step 2: Groq se face description lo pehle (Facebook search ke liye)
        from search.groq_search import describe_face_groq
        face_description = await describe_face_groq(filepath) or ""

        # Step 3: Search all engines in parallel
        search_results = await asyncio.gather(
            search_yandex(filepath),
            search_google(filepath),
            search_bing(filepath),
            search_tineye(filepath),
            search_serpapi(filepath),
            search_facebook(filepath, face_description),
            return_exceptions=True
        )

        all_matches = []
        clean_engines = []
        engine_names = ["Yandex", "Groq AI", "Bing", "TinEye", "Google Lens", "Facebook"]

        for i, result in enumerate(search_results):
            engine_name = engine_names[i]

            if isinstance(result, Exception):
                print(f"⚠️ {engine_name} exception: {str(result)[:80]}")
                clean_engines.append({
                    "engine": engine_name,
                    "status": "Error",
                    "pages_checked": 0
                })
                continue

            if not result or len(result) == 0:
                clean_engines.append({
                    "engine": engine_name,
                    "status": "No matches",
                    "pages_checked": 0
                })
                continue

            try:
                matched = await match_faces(filepath, face_embedding, result)
                if matched:
                    all_matches.extend(matched)
                else:
                    clean_engines.append({
                        "engine": engine_name,
                        "status": "No face match confirmed",
                        "pages_checked": len(result)
                    })
            except Exception as e:
                print(f"⚠️ Match error for {engine_name}: {str(e)[:80]}")
                clean_engines.append({
                    "engine": engine_name,
                    "status": "Match error",
                    "pages_checked": len(result)
                })

        return {
            "matches": all_matches,
            "clean": clean_engines,
            "total_found": len(all_matches)
        }

    except Exception as e:
        print(f"❌ Scan error: {str(e)}")
        return {"error": f"Scan failed: {str(e)}"}

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)