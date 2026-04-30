"""
core/ai_detector.py
────────────────────
AI Detection Module using Hugging Face model.
Primary: prithivMLmods/AI-vs-Real-Image-Detector
Fallback: Organika/sdxl-detector (if primary unavailable)
"""

import io
import logging
from PIL import Image
from transformers import pipeline

logger = logging.getLogger(__name__)

# Model priority list — first available is used
_MODEL_CANDIDATES = [
    "prithivMLmods/AI-vs-Real-Image-Detector",
    "Organika/sdxl-detector",
    "umm-maybe/AI-image-detector",
    "haywoodsloan/ai-image-detector-deploy",
]

_AI_KEYWORDS   = ("ai", "fake", "generated", "artificial", "synthetic", "sdxl", "diffusion")
_REAL_KEYWORDS = ("real", "human", "authentic", "original", "natural", "photo")


class AIDetector:
    """
    Singleton-style AI image detector.
    Loads the best available HuggingFace model once at startup.
    """

    def __init__(self):
        self.pipeline  = None
        self.available = False
        self.model_name = None
        self._load_model()

    def _load_model(self):
        """Load the Hugging Face model once at startup."""
        for model_id in _MODEL_CANDIDATES:
            try:
                logger.info(f"Loading AI model: {model_id}")
                # Use CPU (device=-1) for compatibility; change to 0 if GPU available
                self.pipeline = pipeline(
                    "image-classification",
                    model=model_id,
                    device=-1   # -1 = CPU, 0 = GPU
                )
                self.available  = True
                self.model_name = model_id
                logger.info(f"AI model loaded successfully: {model_id}")
                return
            except Exception as e:
                logger.warning(f"Model {model_id} unavailable: {e}")
                continue

        logger.error("All AI models unavailable — running in rule-only mode")
        self.available = False

    def detect(self, image_bytes: bytes) -> dict:
        """
        Analyze image and return AI score (0-100).
        Higher score = more likely AI-generated.

        Returns
        -------
        {
            'score'      : int     0-100
            'label'      : str     e.g. 'real', 'ai-generated'
            'confidence' : float   raw model confidence 0-100
            'error'      : str|None
        }
        """
        if not self.available:
            return {
                'score': 50, 'label': 'unknown',
                'confidence': 0.0, 'error': 'model offline'
            }

        try:
            # Open and preprocess image
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            # Resize to 512x512 (model input size)
            img = img.resize((512, 512), Image.Resampling.LANCZOS)

            # Run inference
            results = self.pipeline(img)
            ai_score = self._parse_results(results)

            top      = results[0]
            label    = top.get('label', 'unknown').lower()
            confidence = round(top.get('score', 0.0) * 100, 1)

            return {
                'score':      round(ai_score, 1),
                'label':      label,
                'confidence': confidence,
                'error':      None,
            }

        except Exception as e:
            logger.error(f"AI inference error: {e}")
            return {'score': 50, 'label': 'error', 'confidence': 0.0, 'error': str(e)}

    def _parse_results(self, results: list) -> float:
        """Map model output to AI score 0-100."""
        # Priority 1: look for AI-positive label
        for r in results:
            label = r.get('label', '').lower()
            score = r.get('score', 0.0)
            if any(k in label for k in _AI_KEYWORDS):
                return score * 100.0

        # Priority 2: invert real label
        for r in results:
            label = r.get('label', '').lower()
            score = r.get('score', 0.0)
            if any(k in label for k in _REAL_KEYWORDS):
                if 'real' == label:
                    return (1.0 - score) * 100.0  # high confidence real → low AI score
                return (1.0 - score) * 100.0

        # Priority 3: binary classifier fallback
        if len(results) >= 2:
            top = max(results, key=lambda x: x.get('score', 0))
            if any(k in top['label'].lower() for k in _REAL_KEYWORDS):
                return (1.0 - top['score']) * 100.0
            return top['score'] * 100.0

        return 50.0  # neutral fallback
