"""
model/metadata_check.py
───────────────────────
EXIF metadata extraction and risk analysis for return-fraud detection.

Risk scoring (max 20 points):
  +20  Editing software detected (Photoshop / GIMP / etc.)
  +15  Image date newer than "today" (impossible timestamp)
  +10  DateTime field entirely missing
  + 8  No GPS data on an outdoor-damage claim
  + 5  GPS coordinates point to a mismatched region (placeholder)
  + 5  Very small image (< 100×100) — may be placeholder/thumbnail

Returns: (metadata_score: float, reasons: list[str], exif_dict: dict)
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from PIL import Image, ExifTags

# Software strings that suggest image editing
_EDIT_KEYWORDS = {
    "photoshop", "gimp", "lightroom", "capture one",
    "affinity", "snapseed", "vsco", "facetune", "meitu",
    "canva", "picsart", "adobe", "illustrator",
}

# Return reasons that might warrant GPS (outdoor claims)
_OUTDOOR_REASONS = {
    "damaged during delivery",
    "item arrived broken",
    "wrong item received",
    "package damaged",
}


def _tag_name(tag_id: int) -> str:
    return ExifTags.TAGS.get(tag_id, str(tag_id))


def extract_exif(image_bytes: bytes) -> dict[str, Any]:
    """
    Open image and return a flat dict of human-readable EXIF key→value pairs.
    Returns empty dict if no EXIF or on error.
    """
    result: dict[str, Any] = {}
    try:
        img  = Image.open(io.BytesIO(image_bytes))
        result["format"] = img.format or "Unknown"
        result["mode"]   = img.mode
        result["width"]  = img.width
        result["height"] = img.height

        exif_raw = img._getexif()  # type: ignore[attr-defined]
        if not exif_raw:
            return result

        for tag_id, value in exif_raw.items():
            name = _tag_name(tag_id)
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="replace")
                except Exception:
                    value = repr(value)
            result[name] = value

    except Exception:
        pass
    return result


def check_metadata(
    exif: dict[str, Any],
    return_reason: str = "",
) -> tuple[float, list[str]]:
    """
    Evaluate EXIF data and return (risk_points: float 0-20, reasons: list[str]).

    Args:
        exif          : dict from extract_exif()
        return_reason : the reason selected by the user in the dashboard
    """
    risk  = 0.0
    found: list[str] = []

    # ── 1. Editing software ─────────────────────────────────────────────────
    software = str(exif.get("Software", "")).lower()
    if software:
        for kw in _EDIT_KEYWORDS:
            if kw in software:
                risk  = min(20.0, risk + 20.0)
                found.append(
                    f"🖥️ Editing software detected in metadata: **{exif.get('Software')}**"
                )
                break
    else:
        found.append("✅ No editing software tag found")

    # ── 2. Timestamp checks ─────────────────────────────────────────────────
    datetime_str = exif.get("DateTime") or exif.get("DateTimeOriginal") or ""
    if not datetime_str:
        risk  = min(20.0, risk + 10.0)
        found.append("⚠️ No DateTime field in metadata — timestamp verification impossible")
    else:
        found.append(f"📅 Image timestamp: **{datetime_str}**")
        try:
            # Format: "YYYY:MM:DD HH:MM:SS"
            img_dt = datetime.strptime(str(datetime_str), "%Y:%m:%d %H:%M:%S")
            now    = datetime.now()
            if img_dt > now:
                risk  = min(20.0, risk + 15.0)
                found.append("🚨 Image timestamp is in the **future** — impossible, likely tampered")
            elif (now - img_dt).days > 730:
                risk  = min(20.0, risk + 5.0)
                found.append(f"⚠️ Image is over 2 years old ({(now - img_dt).days} days)")
        except ValueError:
            found.append("⚠️ Could not parse timestamp format")

    # ── 3. GPS check for outdoor-damage claims ──────────────────────────────
    has_gps = "GPSInfo" in exif or any(
        k.lower().startswith("gps") for k in exif
    )
    reason_lower = return_reason.lower()
    is_outdoor   = any(r in reason_lower for r in _OUTDOOR_REASONS)

    if is_outdoor and not has_gps:
        risk  = min(20.0, risk + 8.0)
        found.append(
            "📍 GPS data missing for a delivery-damage claim — location cannot be verified"
        )
    elif has_gps:
        found.append("📍 GPS metadata present")

    # ── 4. Suspiciously small image ─────────────────────────────────────────
    w = exif.get("width", 0) or 0
    h = exif.get("height", 0) or 0
    if 0 < w < 100 or 0 < h < 100:
        risk  = min(20.0, risk + 5.0)
        found.append(f"⚠️ Very small image ({w}×{h}px) — may be placeholder/thumbnail")
    elif w and h:
        found.append(f"📐 Image dimensions: **{w} × {h}px**")

    # ── 5. Missing EXIF entirely ────────────────────────────────────────────
    has_real_exif = any(
        k not in {"format", "mode", "width", "height"}
        for k in exif
    )
    if not has_real_exif:
        risk  = min(20.0, risk + 5.0)
        found.append("⚠️ No EXIF metadata at all — image may have been screenshot or stripped")
    else:
        found.append(f"ℹ️ {len(exif)} EXIF fields found")

    return round(risk, 2), found
