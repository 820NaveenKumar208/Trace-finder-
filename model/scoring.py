"""
model/scoring.py
────────────────
Fraud scoring engine for Return Fraud Intelligence System.

Combines three signal sources into a single Fraud Risk Score (0–100):

  Signal              Max pts  Source
  ──────────────────  ───────  ────────────────────────────
  Image similarity      50     CLIP cosine similarity
  Metadata issues       20     EXIF analysis
  User behaviour        30     Historical return patterns

Final Score → Risk Label → Decision
"""

from __future__ import annotations

from typing import Any

# ── Thresholds ───────────────────────────────────────────────────────────────
_HIGH_RISK_THRESHOLD   = 60
_MEDIUM_RISK_THRESHOLD = 30


# ── User behavior scorer ─────────────────────────────────────────────────────

def score_user_behavior(user: dict[str, Any]) -> tuple[float, list[str]]:
    """
    Score user behavior risk (0–30 points).

    Rules:
      - Return ratio > 0.7       → +20 pts   (very high)
      - Return ratio > 0.5       → +12 pts   (high)
      - Return ratio > 0.3       → +6 pts    (moderate)
      - recent_returns ≥ 5       → +10 pts
      - recent_returns ≥ 3       → +5 pts
      - flagged_incidents ≥ 3    → +10 pts
      - flagged_incidents ≥ 1    → +5 pts
      - account_age_days < 60    → +5 pts    (new account)
    """
    reasons: list[str] = []
    score = 0.0

    total_orders  = max(1, user.get("total_orders", 1))
    total_returns = user.get("total_returns", 0)
    recent        = user.get("recent_returns", 0)
    flags         = user.get("flagged_incidents", 0)
    age_days      = user.get("account_age_days", 365)

    ratio = total_returns / total_orders

    # Return ratio
    if ratio > 0.7:
        score += 20
        reasons.append(
            f"🚨 Extremely high return ratio ({ratio:.0%}) — {total_returns}/{total_orders} orders returned"
        )
    elif ratio > 0.5:
        score += 12
        reasons.append(
            f"⚠️ High return ratio ({ratio:.0%}) — {total_returns}/{total_orders} orders returned"
        )
    elif ratio > 0.3:
        score += 6
        reasons.append(
            f"⚠️ Moderate return ratio ({ratio:.0%}) — {total_returns}/{total_orders} orders returned"
        )
    else:
        reasons.append(f"✅ Normal return ratio ({ratio:.0%})")

    # Recent returns velocity
    if recent >= 5:
        score += 10
        reasons.append(f"🚨 {recent} returns in the last 30 days — high velocity")
    elif recent >= 3:
        score += 5
        reasons.append(f"⚠️ {recent} returns recently — elevated activity")
    else:
        reasons.append(f"✅ Low recent return activity ({recent} in last 30 days)")

    # Past fraud flags
    if flags >= 3:
        score += 10
        reasons.append(f"🚨 {flags} prior fraud flags on this account")
    elif flags >= 1:
        score += 5
        reasons.append(f"⚠️ {flags} prior flag(s) on this account")
    else:
        reasons.append("✅ No prior fraud flags")

    # Account age
    if age_days < 60:
        score += 5
        reasons.append(f"⚠️ New account ({age_days} days old) — higher risk profile")
    else:
        reasons.append(f"✅ Established account ({age_days} days old)")

    return round(min(30.0, score), 2), reasons


# ── Main scoring engine ───────────────────────────────────────────────────────

def compute_fraud_score(
    image_score: float,
    metadata_score: float,
    behavior_score: float,
    extra_reasons: list[str] | None = None,
) -> tuple[int, list[str]]:
    """
    Combine all signal scores into a final Fraud Risk Score.

    Args:
        image_score     : 0-50 from image similarity
        metadata_score  : 0-20 from EXIF analysis
        behavior_score  : 0-30 from user behavior

    Returns:
        (final_score: int 0-100, combined_reasons: list[str])
    """
    total  = image_score + metadata_score + behavior_score
    capped = min(100, max(0, round(total)))
    reasons: list[str] = extra_reasons or []
    return capped, reasons


# ── Labels and decisions ──────────────────────────────────────────────────────

def get_risk_label(score: int) -> str:
    """Return human-readable risk tier."""
    if score >= _HIGH_RISK_THRESHOLD:
        return "High Risk"
    elif score >= _MEDIUM_RISK_THRESHOLD:
        return "Medium Risk"
    return "Low Risk"


def get_decision(score: int) -> str:
    """Map score to actionable business decision."""
    if score >= _HIGH_RISK_THRESHOLD:
        return "Send to Manual Review"
    elif score >= _MEDIUM_RISK_THRESHOLD:
        return "Monitor"
    return "Auto Approve"


def get_risk_color(score: int) -> str:
    """Return CSS hex color for the risk level."""
    if score >= _HIGH_RISK_THRESHOLD:
        return "#ef4444"   # red
    elif score >= _MEDIUM_RISK_THRESHOLD:
        return "#f59e0b"   # amber
    return "#22c55e"       # green


def get_risk_emoji(score: int) -> str:
    if score >= _HIGH_RISK_THRESHOLD:
        return "🚨"
    elif score >= _MEDIUM_RISK_THRESHOLD:
        return "⚠️"
    return "✅"


def get_decision_emoji(decision: str) -> str:
    mapping = {
        "Auto Approve":            "✅",
        "Monitor":                 "👁️",
        "Send to Manual Review":   "🔍",
    }
    return mapping.get(decision, "❓")


def score_breakdown(
    image_score: float,
    metadata_score: float,
    behavior_score: float,
) -> list[dict]:
    """Return structured breakdown list for UI table."""
    return [
        {
            "Signal":    "🖼️ Image Similarity",
            "Score":     f"{image_score:.1f}",
            "Max":       "50",
            "Pct":       f"{image_score / 50 * 100:.0f}%",
            "Weight":    "50%",
        },
        {
            "Signal":    "📋 Metadata Analysis",
            "Score":     f"{metadata_score:.1f}",
            "Max":       "20",
            "Pct":       f"{metadata_score / 20 * 100:.0f}%",
            "Weight":    "20%",
        },
        {
            "Signal":    "👤 User Behaviour",
            "Score":     f"{behavior_score:.1f}",
            "Max":       "30",
            "Pct":       f"{behavior_score / 30 * 100:.0f}%",
            "Weight":    "30%",
        },
    ]
