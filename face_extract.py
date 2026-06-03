from deepface import DeepFace
import numpy as np
import cv2

def extract_face(image_path: str):
    backends = ["opencv", "retinaface", "mtcnn"]
    for backend in backends:
        try:
            result = DeepFace.represent(
                img_path=image_path, model_name="Facenet512",
                enforce_detection=True, detector_backend=backend, align=True
            )
            if result:
                best = max(result, key=lambda x: x.get("face_confidence", 0))
                return best["embedding"]
        except:
            continue
    try:
        result = DeepFace.represent(img_path=image_path, model_name="Facenet512",
            enforce_detection=False, detector_backend="opencv", align=True)
        if result: return result[0]["embedding"]
    except: pass
    return None

def extract_face_crop(image_path: str):
    try:
        faces = DeepFace.extract_faces(img_path=image_path,
            detector_backend="opencv", enforce_detection=True, align=True)
        if faces:
            import tempfile
            best = max(faces, key=lambda x: x.get("confidence", 0))
            face_img = best["face"]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            cv2.imwrite(tmp.name, cv2.cvtColor(
                (face_img * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
            return tmp.name
    except: pass
    return image_path

def compare_faces(embedding1: list, embedding2: list, threshold: float = 0.5) -> dict:
    try:
        v1 = np.array(embedding1, dtype=np.float32)
        v2 = np.array(embedding2, dtype=np.float32)
        v1 = v1 / (np.linalg.norm(v1) + 1e-9)
        v2 = v2 / (np.linalg.norm(v2) + 1e-9)
        sim = float(np.dot(v1, v2))
        euc = float(np.linalg.norm(v1 - v2))
        conf = max(0, min(100, int(sim * 100)))
        return {"matched": (1-sim) < threshold and euc < 0.9,
                "confidence": conf, "cosine_sim": round(sim,4), "euclidean": round(euc,4)}
    except:
        return {"matched": False, "confidence": 0, "cosine_sim": 0, "euclidean": 9}