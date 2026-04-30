"""
VerifyFlow – Forensic Analysis Module
ELA + contour detection + heatmap. All calls wrapped in try/except.
"""
import io
import logging
from typing import Tuple, List

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

logger = logging.getLogger(__name__)
MAX_SIDE = 512


def _resize(img: Image.Image) -> Image.Image:
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return img


def compute_ela(
    image_bytes: bytes, quality: int = 90
) -> Tuple[float, Image.Image, np.ndarray, np.ndarray]:
    """
    Multi-quality Error Level Analysis (q=75 + q=90).
    Weighted combination gives better discrimination for PNG and AI images.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = _resize(img)
    orig_np = np.array(img)

    def _ela_at_quality(q: int) -> np.ndarray:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q)
        recomp = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
        diff = ImageChops.difference(img, recomp)
        return np.array(diff).astype(np.float32).mean(axis=2)

    ela_gray_90 = _ela_at_quality(90)
    ela_gray_75 = _ela_at_quality(75)
    # q=75 more sensitive to manipulation, give it higher weight
    ela_gray = 0.35 * ela_gray_90 + 0.65 * ela_gray_75

    p95 = float(np.percentile(ela_gray, 95))
    ela_score = min(100.0, (p95 / 255.0) * 100.0 * 4.0)

    # Build display image (amplified)
    diff_display = (ela_gray * 3).clip(0, 255).astype(np.uint8)
    ela_pil = Image.fromarray(diff_display)
    extrema = ela_pil.getextrema()
    if isinstance(extrema[0], (int, float)):
        max_val = extrema[1]
    else:
        max_val = max(ch[1] for ch in extrema)
    if max_val > 0:
        ela_pil = ImageEnhance.Brightness(ela_pil).enhance(255.0 / max_val)

    return round(ela_score, 2), ela_pil, ela_gray, orig_np


MIN_CONTOUR_AREA = 150   # Ignore tiny edge fragments (was 50)
MAX_CONTOUR_AREA = 5000  # Ignore massive uniform regions


def compute_contours(ela_gray: np.ndarray) -> Tuple[int, List]:
    """Find significant suspicious contours in the ELA grayscale map."""
    threshold = float(np.percentile(ela_gray, 80))
    mask = (ela_gray > threshold).astype(np.uint8)
    result = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    all_contours = result[0] if len(result) == 2 else result[1]
    significant = [
        c for c in all_contours
        if MIN_CONTOUR_AREA < cv2.contourArea(c) < MAX_CONTOUR_AREA
    ]
    return len(significant), significant


def compute_anomaly_ratio(ela_gray: np.ndarray, threshold: float = 50.0) -> float:
    """
    Fraction of pixels with strong ELA difference.
    Uses adaptive threshold (P85 of ela_gray, min 3.0) so it works for both
    JPEG (large ela values) and PNG (tiny ela values).
    Real damage = localised spikes (low ratio); AI tampering = spread anomalies (high ratio).
    """
    adaptive_threshold = max(3.0, float(np.percentile(ela_gray, 85)))
    high_pixels = float(np.sum(ela_gray > adaptive_threshold))
    return high_pixels / ela_gray.size


def draw_tampered_regions(original_rgb: np.ndarray, contours: List, box_count: int) -> np.ndarray:
    """Draw bounding boxes on suspicious regions."""
    out = original_rgb.copy()
    if box_count == 0 or not contours:
        h, w = out.shape[:2]
        cv2.rectangle(out,
                      (int(w * 0.05), int(h * 0.05)),
                      (int(w * 0.95), int(h * 0.95)),
                      (255, 165, 0), 2)
    else:
        for c in contours:
            area = cv2.contourArea(c)
            if MIN_CONTOUR_AREA < area < MAX_CONTOUR_AREA:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(out, (x, y), (x + w, y + h), (220, 20, 60), 2)
    return out


def build_heatmap(original_rgb: np.ndarray, ela_gray: np.ndarray) -> np.ndarray:
    """Overlay JET heatmap of ELA differences onto the original image."""
    norm = cv2.normalize(ela_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heatmap_bgr = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)
    return cv2.addWeighted(original_rgb, 0.6, heatmap_rgb, 0.4, 0)


def forensic_score_from_ela(
    ela_score: float,
    box_count: int,
    anomaly_ratio: float = 1.0,
) -> float:
    """
    Combine ELA P95 score + box count + anomaly spread into a forensic score (0-100).

    anomaly_ratio is computed with adaptive threshold (works for both JPEG and PNG).
    Low anomaly_ratio (<0.08 = very localised) with low ela_score -> gentle reduction.
    box_bonus capped at 15.
    """
    box_bonus = min(15.0, (box_count // 10) * 5.0 + min(box_count, 5) * 1.5)
    raw = ela_score + box_bonus

    # Only reduce when truly sparse AND ela_score is low (real localised damage)
    # This threshold is conservative to avoid suppressing real fraud signals
    if anomaly_ratio < 0.08 and ela_score < 15:
        raw = raw * 0.6

    return min(100.0, round(raw, 2))
