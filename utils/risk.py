"""
utils/risk.py
─────────────
Rule-based fraud risk scoring engine.

3-Layer Detection Pipeline:
  Layer 1: AI Image Authenticity  → ai_generated flag (+30 if fake)
  Layer 2: Metadata + Rules       → hash, size, EXIF, frequency
  Layer 3: Blockchain             → log only if risk > 60

Scoring rules:
  +30  AI model detected image as AI-generated / fake
  +50  Duplicate image hash detected
  +20  File size suspiciously small (< 20 KB)
  +10  EXIF metadata missing entirely
  +20  High upload frequency (> 3 uploads in 60s)
  +15  Editing software detected in EXIF

Classification:
   0–30  → Low Risk    ✅
  31–70  → Medium Risk ⚠️
  71–100 → High Risk   🚨
"""

from typing import Any

EDITING_SOFTWARE = {
    "photoshop", "gimp", "lightroom", "affinity",
    "snapseed", "picsart", "canva", "meitu", "facetune",
}

MIN_SAFE_SIZE_KB   = 20   # Images under this are suspicious
HIGH_FREQ_THRESHOLD = 3   # More than 3 uploads in 60s is suspicious
BLOCKCHAIN_THRESHOLD = 60 # Only log to blockchain above this score


def compute_risk_score(
    is_duplicate: bool,
    metadata: dict[str, Any],
    recent_upload_count: int,
    ai_generated: bool = False,
    ai_score: float = 0.0,
) -> tuple[int, list[str]]:
    """
    Compute combined fraud risk score from all 3 detection layers.

    Parameters
    ----------
    is_duplicate        : bool   Layer 2 – duplicate hash detected
    metadata            : dict   Layer 2 – file/EXIF metadata
    recent_upload_count : int    Layer 2 – uploads in last 60s
    ai_generated        : bool   Layer 1 – HuggingFace model says AI/fake
    ai_score            : float  Layer 1 – AI confidence 0–100

    Returns
    -------
    score   : int          0–100
    reasons : list[str]    Human-readable explanation bullets
    """
    score = 0
    reasons: list[str] = []

    # ── Layer 1: AI Detection ──────────────────────────────────────────────
    if ai_generated:
        score += 30
        reasons.append(f"🤖 **AI-generated image detected** — model confidence: {ai_score:.0f}% (+30)")

    # ── Layer 2: Rule-Based Metadata ───────────────────────────────────────
    # Rule: Duplicate image hash
    if is_duplicate:
        score += 50
        reasons.append("🔁 **Duplicate image** — same image submitted before (+50)")

    # Rule: Suspiciously small file
    size_kb = metadata.get("file_size_kb", 999)
    if size_kb < MIN_SAFE_SIZE_KB:
        score += 20
        reasons.append(f"📦 **File too small** ({size_kb:.1f} KB) — may be a thumbnail (+20)")

    # Rule: Missing EXIF metadata
    if not metadata.get("has_exif", False):
        score += 10
        reasons.append("📋 **No EXIF metadata** — screenshot or stripped image (+10)")

    # Rule: High upload frequency
    if recent_upload_count > HIGH_FREQ_THRESHOLD:
        score += 20
        reasons.append(f"⏱️ **High upload frequency** — {recent_upload_count} images in last 60s (+20)")

    # Rule: Editing software in EXIF
    software = metadata.get("software", "").lower()
    for kw in EDITING_SOFTWARE:
        if kw in software:
            score += 15
            reasons.append(f"🖥️ **Editing software detected**: {metadata.get('software')} (+15)")
            break

    if not reasons:
        reasons.append("✅ No suspicious signals detected — image appears legitimate")

    score = min(100, max(0, score))
    return score, reasons


def classify_risk(score: int) -> tuple[str, str, str]:
    """Returns (label, emoji, color_hex)."""
    if score >= 71:
        return "HIGH RISK",   "🚨", "#EF4444"
    elif score >= 31:
        return "MEDIUM RISK", "⚠️", "#F59E0B"
    return "LOW RISK",        "✅", "#22C55E"


def should_log_blockchain(score: int) -> bool:
    """Layer 3: Only log to blockchain if risk score exceeds threshold."""
    return score > BLOCKCHAIN_THRESHOLD

