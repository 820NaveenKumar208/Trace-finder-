"""
core/risk_engine.py
────────────────────
compute_final_risk() — combines Layer 1 (AI) + Layer 2 (Rules).
Verdict: REAL ≤35 / REVIEW 35-70 / FRAUD >70
Blockchain trigger: final > 70
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ai_detector import AIDetector
from core.rule_scorer import calculate_rule_score, extract_metadata, compute_hash

import logging
logger = logging.getLogger(__name__)

# Initialize AI detector once (global singleton)
ai_detector = AIDetector()


def compute_final_risk(image_bytes: bytes, filename: str = "upload") -> dict:
    """
    Full 3-layer fraud detection pipeline.

    Returns
    -------
    {
        'ai_score'           : float|None   0-100 (None if offline)
        'rule_score'         : int          0-100
        'final_score'        : float        0-100
        'verdict'            : str          REAL / REVIEW / FRAUD
        'reasons'            : list[str]
        'ai_model_available' : bool
        'image_hash'         : str
        'metadata'           : dict
    }
    """
    # ── Layer 1: AI Score ─────────────────────────────────────────────────
    ai_result      = ai_detector.detect(image_bytes)
    ai_score       = ai_result['score']      if ai_detector.available else None
    ai_confidence  = ai_result['confidence'] if ai_detector.available else 0.0
    ai_label       = ai_result['label']      if ai_detector.available else 'unknown'

    # ── Layer 2: Rule Score ───────────────────────────────────────────────
    image_hash  = compute_hash(image_bytes)
    metadata    = extract_metadata(image_bytes, filename)
    rule_score, rule_reasons = calculate_rule_score(image_hash, metadata)

    # ── Layer 3 gate: Combine scores ──────────────────────────────────────
    if ai_score is not None:
        final = (0.6 * ai_score) + (0.4 * rule_score)
    else:
        final = float(rule_score)   # AI offline fallback

    final = round(min(100.0, max(0.0, final)), 1)

    # ── Verdict ───────────────────────────────────────────────────────────
    if final <= 35:
        verdict = "REAL"
    elif final <= 70:
        verdict = "REVIEW"
    else:
        verdict = "FRAUD"

    # ── Reasons ───────────────────────────────────────────────────────────
    reasons = []
    if ai_score is not None:
        if ai_score > 70:
            reasons.append(f"🤖 AI model: likely AI-generated (score {ai_score}/100)")
        elif ai_score < 30:
            reasons.append(f"🤖 AI model: confident this is a real image (score {ai_score}/100)")
        else:
            reasons.append(f"🤖 AI model: uncertain (score {ai_score}/100)")
    else:
        reasons.append("🤖 AI model offline — using rule engine only")
    reasons.extend(rule_reasons)
    if not rule_reasons:
        reasons.append("✅ No rule-based fraud signals detected")

    # ── System Confidence ─────────────────────────────────────────────────
    # How certain is the overall system? Based on AI confidence + rule clarity
    if ai_detector.available and ai_confidence > 0:
        # High when AI is decisive (far from 50%) AND rule score is clear
        ai_certainty   = abs(ai_score - 50) * 2          # 0-100
        rule_certainty = 100 - min(rule_score, 50) * 2   # high when rule_score low
        sys_conf = round((0.6 * ai_certainty + 0.4 * rule_certainty), 1)
    else:
        sys_conf = round(100 - abs(rule_score - 50), 1)

    sys_conf = min(100.0, max(0.0, sys_conf))
    if sys_conf >= 75:   conf_label = "HIGH"
    elif sys_conf >= 45: conf_label = "MEDIUM"
    else:                conf_label = "LOW"

    return {
        'ai_score':            ai_score,
        'ai_confidence':       ai_confidence,
        'ai_label':            ai_label,
        'rule_score':          rule_score,
        'final_score':         final,
        'verdict':             verdict,
        'reasons':             reasons,
        'ai_model_available':  ai_detector.available,
        'image_hash':          image_hash,
        'metadata':            metadata,
        'system_confidence':   sys_conf,
        'confidence_label':    conf_label,
    }
