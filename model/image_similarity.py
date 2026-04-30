"""
model/image_similarity.py
─────────────────────────
CLIP-based image similarity engine.

Loads openai/clip-vit-base-patch32 (cached after first download ~350 MB).
Compares an uploaded image against two libraries:
  - data/product_images/  (legitimate product photos)
  - data/fraud_images/    (known reused / fraudulent photos)

Returns:
  image_score   : float  0-50 points for the fraud scoring engine
  reasons       : list[str]
  best_match    : dict | None   {"path": ..., "similarity": ..., "library": ...}
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

# ── Optional heavy imports ──────────────────────────────────────────────────
try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
    _CLIP_AVAILABLE = True
except ImportError:
    _CLIP_AVAILABLE = False

# ── Constants ───────────────────────────────────────────────────────────────
_DATA_DIR     = Path(__file__).resolve().parent.parent / "data"
PRODUCT_DIR   = _DATA_DIR / "product_images"
FRAUD_DIR     = _DATA_DIR / "fraud_images"
MODEL_ID      = "openai/clip-vit-base-patch32"
SIM_THRESHOLD = 0.82   # cosine similarity flag threshold

_model: Optional[object]     = None
_processor: Optional[object] = None


def _load_clip() -> bool:
    """Load CLIP model once; return True on success."""
    global _model, _processor
    if _model is not None:
        return True
    if not _CLIP_AVAILABLE:
        return False
    try:
        _processor = CLIPProcessor.from_pretrained(MODEL_ID)
        _model     = CLIPModel.from_pretrained(MODEL_ID)
        _model.eval()
        return True
    except Exception:
        return False


def _get_embedding(pil_img: Image.Image) -> np.ndarray:
    """Return L2-normalised CLIP visual embedding as 1-D numpy array."""
    inputs = _processor(images=pil_img, return_tensors="pt")
    with torch.no_grad():
        feats = _model.get_image_features(**inputs)
    feats = feats.squeeze(0).cpu().numpy().astype(np.float32)
    norm  = np.linalg.norm(feats)
    return feats / (norm + 1e-9)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # both already L2-normalised


def _scan_library(
    query_emb: np.ndarray,
    directory: Path,
    library_label: str,
) -> tuple[float, Optional[dict]]:
    """
    Compare query against every image in `directory`.
    Returns (max_similarity, best_match_info | None).
    """
    if not directory.exists():
        return 0.0, None

    exts  = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    files = [p for p in directory.iterdir() if p.suffix.lower() in exts]
    if not files:
        return 0.0, None

    best_sim  = 0.0
    best_path = None

    for fp in files:
        try:
            img     = Image.open(fp).convert("RGB")
            emb     = _get_embedding(img)
            sim     = _cosine(query_emb, emb)
            if sim > best_sim:
                best_sim  = sim
                best_path = fp
        except Exception:
            continue

    match_info = (
        {"path": str(best_path), "similarity": best_sim, "library": library_label}
        if best_path else None
    )
    return best_sim, match_info


def analyze_image_similarity(
    pil_img: Image.Image,
) -> dict:
    """
    Main entry point called by app.py.

    Returns:
        {
          "image_score": float,        # 0-50 contribution to fraud score
          "reasons":     list[str],
          "best_match":  dict | None,  # {"path", "similarity", "library"}
          "product_sim": float,
          "fraud_sim":   float,
          "clip_online": bool,
        }
    """
    reasons: list[str] = []
    image_score        = 0.0
    product_sim        = 0.0
    fraud_sim          = 0.0
    best_match         = None

    clip_ok = _load_clip()

    if not clip_ok:
        reasons.append("ℹ️ CLIP model unavailable – image similarity skipped")
        return {
            "image_score": 0.0,
            "reasons":     reasons,
            "best_match":  None,
            "product_sim": 0.0,
            "fraud_sim":   0.0,
            "clip_online": False,
        }

    # Compute query embedding
    query_emb = _get_embedding(pil_img)

    # --- Compare against known fraud images (highest weight) ----------------
    fraud_sim, fraud_match = _scan_library(query_emb, FRAUD_DIR,  "Fraud Library")

    # --- Compare against product images (possible reuse detection) ----------
    product_sim, prod_match = _scan_library(query_emb, PRODUCT_DIR, "Product Library")

    # --- Determine best overall match ---------------------------------------
    if fraud_sim >= product_sim:
        best_match = fraud_match
    elif product_sim > 0:
        best_match = prod_match

    # --- Score and reasons -------------------------------------------------
    if fraud_sim >= SIM_THRESHOLD:
        image_score = 50.0
        reasons.append(
            f"🚨 High similarity to known fraud image ({fraud_sim:.1%}) — likely reused photo"
        )
    elif fraud_sim >= 0.65:
        image_score = max(image_score, 30.0)
        reasons.append(
            f"⚠️ Moderate match to fraud image database ({fraud_sim:.1%})"
        )

    if product_sim >= SIM_THRESHOLD:
        image_score = max(image_score, 40.0)
        reasons.append(
            f"🔁 Image closely matches existing product listing ({product_sim:.1%}) — possible copy"
        )
    elif product_sim >= 0.65:
        image_score = max(image_score, 20.0)
        reasons.append(
            f"⚠️ Partial match to product catalogue ({product_sim:.1%})"
        )

    if image_score == 0.0 and (fraud_sim > 0 or product_sim > 0):
        reasons.append(
            f"✅ No suspicious image match (fraud sim: {fraud_sim:.1%}, product sim: {product_sim:.1%})"
        )
    elif image_score == 0.0:
        reasons.append("✅ No reference images in library — cannot compare")

    return {
        "image_score": image_score,
        "reasons":     reasons,
        "best_match":  best_match,
        "product_sim": product_sim,
        "fraud_sim":   fraud_sim,
        "clip_online": True,
    }
