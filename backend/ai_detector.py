"""
VerifyFlow – AI Detector Module
Tries multiple HuggingFace models in priority order.
Falls back gracefully to neutral 50.0 if all fail.
"""
import io
import logging
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Priority list — first working model is used
_MODEL_CANDIDATES = [
    "Organika/sdxl-detector",
    "umm-maybe/AI-image-detector",
    "haywoodsloan/ai-image-detector-deploy",
    "prithivMLmods/AI-vs-Real-Image-Detector",
]

_AI_KEYWORDS   = ("ai", "fake", "generated", "artificial", "synthetic", "sdxl", "diffusion", "midjourney")
_REAL_KEYWORDS = ("real", "human", "authentic", "original", "natural", "photo")

_detector = None
_loaded_model = None


def _load():
    global _detector, _loaded_model
    if _detector is not None:
        return _detector
    try:
        from transformers import pipeline
        for model_id in _MODEL_CANDIDATES:
            try:
                logger.info(f"Trying model: {model_id}")
                _detector = pipeline("image-classification", model=model_id, device=-1)
                _loaded_model = model_id
                logger.info(f"Model loaded: {model_id}")
                return _detector
            except Exception as e:
                logger.warning(f"Model {model_id} failed: {e}")
                continue
    except Exception as e:
        logger.error(f"transformers not available: {e}")
    return None


def detect_ai(image_bytes: bytes) -> Tuple[float, bool]:
    """
    Returns
    -------
    ai_score : float  0-100  (higher = more likely AI/fake)
    ok       : bool   True if a model ran; False = forensic fallback
    """
    try:
        det = _load()
        if det is None:
            return 50.0, False

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((512, 512), Image.Resampling.LANCZOS)

        results = det(img)
        ai_score = 0.0
        found = False

        # Priority 1: look for AI-positive label
        for r in results:
            label = r.get("label", "").lower()
            score = r.get("score", 0.0)
            if any(k in label for k in _AI_KEYWORDS):
                ai_score = score * 100.0
                found = True
                break

        # Priority 2: invert the "real" label score
        if not found:
            for r in results:
                label = r.get("label", "").lower()
                score = r.get("score", 0.0)
                if any(k in label for k in _REAL_KEYWORDS):
                    ai_score = (1.0 - score) * 100.0
                    found = True
                    break

        # Priority 3: use highest-score label if binary classifier
        if not found and len(results) == 2:
            # Assume binary: pick whichever label seems more "fake"
            sorted_r = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            top = sorted_r[0]
            top_label = top.get("label", "").lower()
            top_score = top.get("score", 0.0)
            # If top label sounds real → invert
            if any(k in top_label for k in _REAL_KEYWORDS):
                ai_score = (1.0 - top_score) * 100.0
            else:
                ai_score = top_score * 100.0
            found = True

        if not found:
            ai_score = 50.0

        logger.info(f"AI score: {ai_score:.1f} (model: {_loaded_model})")
        return round(ai_score, 2), True

    except Exception as e:
        logger.error(f"AI inference error: {e}")
        return 50.0, False
