"""
core/rule_scorer.py
────────────────────
Rule-based scoring engine (Layer 2).
Provides: calculate_rule_score(), extract_metadata(), is_duplicate()
"""

import io
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

STORAGE_PATH = Path(__file__).resolve().parent.parent / "storage" / "hashes.json"

EDITING_SOFTWARE = {
    "photoshop", "gimp", "lightroom", "affinity",
    "snapseed", "picsart", "canva", "meitu", "facetune",
}


# ── Hash helpers ─────────────────────────────────────────────────────────────

def compute_hash(image_bytes: bytes) -> str:
    """Return SHA-256 hex digest of image bytes."""
    return hashlib.sha256(image_bytes).hexdigest()


def _load_store() -> dict:
    try:
        if STORAGE_PATH.exists():
            return json.loads(STORAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_store(store: dict) -> None:
    try:
        STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORAGE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")
    except Exception:
        pass


def is_duplicate(image_hash: str) -> tuple[bool, int]:
    """
    Check if hash was seen before and register it.

    Returns
    -------
    (is_dup, submission_count)
    """
    store = _load_store()
    entry = store.get(image_hash, {"count": 0, "first_seen": None})
    is_dup = entry["count"] > 0
    entry["count"] += 1
    entry["last_seen"] = datetime.utcnow().isoformat()
    if not entry["first_seen"]:
        entry["first_seen"] = entry["last_seen"]
    store[image_hash] = entry
    _save_store(store)
    return is_dup, entry["count"]


def get_recent_count(window_seconds: int = 60) -> int:
    """Count unique images submitted in the last window_seconds."""
    store = _load_store()
    now   = datetime.utcnow()
    count = 0
    for entry in store.values():
        last = entry.get("last_seen", "")
        if last:
            try:
                if (now - datetime.fromisoformat(last)).total_seconds() < window_seconds:
                    count += 1
            except Exception:
                pass
    return count


def get_all_hashes() -> dict:
    """Return the full hash store (for dashboard)."""
    return _load_store()


# ── Metadata ─────────────────────────────────────────────────────────────────

def extract_metadata(image_bytes: bytes, filename: str = "upload") -> dict:
    """
    Extract image metadata and EXIF info.

    Returns dict with: size, size_kb, width, height, format,
    has_exif, camera_make, camera_model, software, timestamp
    """
    meta = {
        "filename":    filename,
        "size":        len(image_bytes),
        "size_kb":     round(len(image_bytes) / 1024, 2),
        "timestamp":   datetime.utcnow().isoformat(),
        "width":       None,
        "height":      None,
        "format":      "Unknown",
        "has_exif":    False,
        "camera_make": "N/A",
        "camera_model":"N/A",
        "software":    "N/A",
        "datetime_original": "N/A",
    }
    try:
        img = Image.open(io.BytesIO(image_bytes))
        meta["width"]  = img.width
        meta["height"] = img.height
        meta["format"] = img.format or "Unknown"

        raw_exif = None
        try:
            raw_exif = img._getexif()  # type: ignore
        except Exception:
            pass

        if raw_exif:
            meta["has_exif"] = True
            exif = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}
            meta["camera_make"]       = str(exif.get("Make", "N/A"))
            meta["camera_model"]      = str(exif.get("Model", "N/A"))
            meta["software"]          = str(exif.get("Software", "N/A"))
            meta["datetime_original"] = str(exif.get("DateTimeOriginal",
                                             exif.get("DateTime", "N/A")))
    except Exception as e:
        logger.warning(f"Metadata extraction error: {e}")

    return meta


# ── Rule Scorer ───────────────────────────────────────────────────────────────

def calculate_rule_score(image_hash: str, metadata: dict) -> tuple[int, list[str]]:
    """
    Rule-based fraud risk scoring (Layer 2).

    Rules:
      +50  Duplicate image hash
      +20  File size < 5 KB
      +10  Missing EXIF metadata
      +20  High upload frequency (> 3 in 60s)
      +15  Editing software detected in EXIF

    Returns
    -------
    (rule_score 0-100, reasons list[str])
    """
    score   = 0
    reasons = []

    # Rule 1: Duplicate hash
    is_dup, dup_count = is_duplicate(image_hash)
    if is_dup:
        score += 50
        reasons.append(f"🔁 Duplicate image hash — submitted {dup_count}× before (+50)")

    # Rule 2: File too small
    if metadata.get("size", 0) < 5000:
        score += 20
        reasons.append(f"📦 File too small ({metadata['size']} bytes) — likely thumbnail (+20)")

    # Rule 3: No EXIF
    if not metadata.get("has_exif", False):
        score += 10
        reasons.append("📋 No EXIF metadata — screenshot or stripped image (+10)")

    # Rule 4: High frequency
    recent = get_recent_count(60)
    if recent > 3:
        score += 20
        reasons.append(f"⏱️ High upload frequency — {recent} images in last 60s (+20)")

    # Rule 5: Editing software
    software = metadata.get("software", "").lower()
    for kw in EDITING_SOFTWARE:
        if kw in software:
            score += 15
            reasons.append(f"🖥️ Editing software detected: {metadata.get('software')} (+15)")
            break

    return min(100, max(0, score)), reasons
