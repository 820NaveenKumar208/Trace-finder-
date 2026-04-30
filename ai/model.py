"""
ai/model.py
───────────
Layer 1: AI Image Authenticity Detector
Uses Organika/sdxl-detector (best available public model for AI vs Real detection).
Falls back gracefully if model is unavailable.
"""
from transformers import pipeline
from PIL import Image
import io

# Load model once at startup (cached globally)
_classifier = None

def _load_model():
    global _classifier
    if _classifier is not None:
        return _classifier
    # Try multiple models in priority order
    for model_id in [
        "Organika/sdxl-detector",
        "umm-maybe/AI-image-detector",
        "haywoodsloan/ai-image-detector-deploy",
    ]:
        try:
            _classifier = pipeline("image-classification", model=model_id, device=-1)
            print(f"[VerifyFlow] AI model loaded: {model_id}")
            return _classifier
        except Exception as e:
            print(f"[VerifyFlow] Model {model_id} unavailable: {e}")
    return None


def detect_ai_image(image_bytes: bytes) -> dict:
    """
    Detect if an image is AI-generated or real.

    Parameters
    ----------
    image_bytes : bytes   Raw image file bytes

    Returns
    -------
    {
        "ai_flag"    : bool    True if image is AI-generated
        "ai_score"   : float   Confidence 0–100 (higher = more likely AI/fake)
        "label"      : str     "AI-Generated" or "Real"
        "model_ok"   : bool    False if model was unavailable
    }
    """
    try:
        clf = _load_model()
        if clf is None:
            return {"ai_flag": False, "ai_score": 0.0, "label": "Unknown", "model_ok": False}

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        results = clf(img)

        ai_keywords   = ("ai", "fake", "generated", "artificial", "synthetic", "sdxl", "diffusion")
        real_keywords = ("real", "human", "authentic", "original", "natural", "photo")

        ai_score = 0.0
        for r in results:
            label = r.get("label", "").lower()
            score = r.get("score", 0.0)
            if any(k in label for k in ai_keywords):
                ai_score = score * 100.0
                break
        else:
            for r in results:
                label = r.get("label", "").lower()
                score = r.get("score", 0.0)
                if any(k in label for k in real_keywords):
                    ai_score = (1.0 - score) * 100.0
                    break
            else:
                # Binary classifier fallback
                if len(results) >= 2:
                    top = max(results, key=lambda x: x.get("score", 0))
                    if any(k in top["label"].lower() for k in real_keywords):
                        ai_score = (1.0 - top["score"]) * 100.0
                    else:
                        ai_score = top["score"] * 100.0

        ai_flag = ai_score > 60.0
        return {
            "ai_flag":  ai_flag,
            "ai_score": round(ai_score, 2),
            "label":    "AI-Generated" if ai_flag else "Real",
            "model_ok": True,
        }

    except Exception as e:
        print(f"[VerifyFlow] AI detection error: {e}")
        return {"ai_flag": False, "ai_score": 0.0, "label": "Error", "model_ok": False}
