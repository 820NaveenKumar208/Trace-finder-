"""
utils/risk_engine.py
────────────────────
Layer 2: Rule-based fraud risk scoring engine.

Rules:
  +50  is_duplicate  → same image submitted before
  +20  file_size < 5000 bytes → suspiciously small
  +10  not has_exif  → metadata stripped or screenshot
  +30  ai_flag       → AI model flagged as generated/fake
  +20  high_frequency → >3 uploads in last 60s

Classification:
   0–30  → Low Risk    ✅
  31–70  → Medium Risk ⚠️
  71–100 → High Risk   🚨

Blockchain threshold: only log if risk > 60
"""

BLOCKCHAIN_THRESHOLD = 60


def calculate_risk(
    is_duplicate: bool,
    file_size: int,
    has_exif: bool,
    ai_flag: bool,
    high_frequency: bool = False,
) -> tuple[int, list[str]]:
    """
    Calculate fraud risk score from all detection signals.

    Parameters
    ----------
    is_duplicate    : bool   Duplicate hash detected (Layer 2)
    file_size       : int    File size in bytes
    has_exif        : bool   EXIF metadata present
    ai_flag         : bool   AI model says image is AI-generated (Layer 1)
    high_frequency  : bool   >3 images uploaded in last 60s

    Returns
    -------
    risk    : int          0–100 final risk score
    reasons : list[str]   Human-readable flags
    """
    risk = 0
    reasons: list[str] = []

    # Layer 1 signal
    if ai_flag:
        risk += 30
        reasons.append("🤖 AI-generated image detected (+30)")

    # Layer 2 signals
    if is_duplicate:
        risk += 50
        reasons.append("🔁 Duplicate image hash detected (+50)")

    if file_size < 5000:
        risk += 20
        reasons.append(f"📦 File too small ({file_size} bytes) — likely thumbnail (+20)")

    if not has_exif:
        risk += 10
        reasons.append("📋 No EXIF metadata — screenshot or stripped (+10)")

    if high_frequency:
        risk += 20
        reasons.append("⏱️ High upload frequency detected (+20)")

    if not reasons:
        reasons.append("✅ No suspicious signals detected")

    return min(100, max(0, risk)), reasons


def classify_risk(risk: int) -> tuple[str, str, str]:
    """Returns (label, emoji, hex_color)."""
    if risk >= 71:
        return "HIGH RISK",   "🚨", "#EF4444"
    elif risk >= 31:
        return "MEDIUM RISK", "⚠️", "#F59E0B"
    return "LOW RISK",        "✅", "#22C55E"


def should_log_blockchain(risk: int) -> bool:
    """Layer 3 gate: only log to blockchain if risk > 60."""
    return risk > BLOCKCHAIN_THRESHOLD
