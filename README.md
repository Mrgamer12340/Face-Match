# 🛡️ FaceGuard

A reverse face search tool that takes an uploaded photo and hunts for that face across the web — checking multiple search engines at the same time and confirming matches using AI-powered face comparison.

---

## What it does

You upload a photo. FaceGuard extracts the face from it, searches across Yandex, Bing, TinEye, Google Lens, and Facebook simultaneously, then verifies each result by comparing face embeddings — so you only get real matches, not random lookalikes.

It also uses Groq's Llama 3.3 model to generate a natural language description of the face, which improves search accuracy especially for Facebook.

---

## How it works

1. **Face extraction** — the uploaded image is processed to detect and extract the face
2. **AI description** — Groq generates a text description of the face for context-aware searching
3. **Parallel search** — all five search engines are queried at the same time using async requests
4. **Face matching** — results are filtered by comparing face embeddings against the original
5. **Response** — confirmed matches are returned along with which engines found nothing

---

## Tech Stack

| Layer           | Tool                              |
|-----------------|-----------------------------------|
| API Framework   | FastAPI + Uvicorn                 |
| Face ML         | DeepFace / face_recognition       |
| AI Description  | Groq API (Llama 3.3)              |
| Search Engines  | Yandex, Bing, TinEye, SerpAPI, Facebook |
| Language        | Python 3.10+                      |

---

## API

Exposes a single endpoint — `POST /scan` — which accepts an image file and returns a JSON response containing confirmed face matches, which engines found nothing, and the total match count.

---

## Project Structure

The project is organized into a main API entry point, a face extraction module, a face matching module, and a search folder containing one file per search engine integration.

Uploaded files are temporarily saved during processing and automatically deleted afterward — nothing is stored permanently.

---

## Environment Variables

Requires API keys for Groq, SerpAPI, and Bing to be set in a `.env` file before running.

---

## ⚠️ Disclaimer

This tool is intended for **personal privacy protection** and **ethical OSINT research only**.  
Do not use it to track, surveil, or identify individuals without their consent.

---

## License
