import sys
sys.path.insert(0, 'backend')
from forensics import compute_ela, compute_contours, compute_anomaly_ratio, forensic_score_from_ela
from ai_detector import detect_ai
from pathlib import Path

def final_score(ai, forensic, ai_ok):
    if not ai_ok:
        return round(forensic, 2)
    if ai >= 65:
        s = 0.75 * ai + 0.25 * forensic
    elif ai <= 30:
        s = 0.75 * ai + 0.25 * forensic
    else:
        s = 0.35 * ai + 0.65 * forensic
    return round(min(100, max(0, s)), 2)

def verdict(f, ai, forensic, ai_ok):
    if ai_ok and ai < 25 and forensic < 15:
        return "REAL"
    if not ai_ok and forensic < 12:
        return "REAL"
    if f >= 60:
        v = "AI-ALTERED"
    elif f >= 35:
        v = "REVIEW"
    else:
        v = "REAL"
    if v == "AI-ALTERED" and not ai_ok and forensic < 35:
        v = "REVIEW"
    if v == "REAL" and forensic > 55:
        v = "REVIEW"
    if ai_ok and ai > 80 and forensic > 40:
        v = "AI-ALTERED"
    return v

images = {
    "product_headphones (EXPECTED=REAL)":  "data/product_images/product_headphones.png",
    "product_smartphone (EXPECTED=REAL)":  "data/product_images/product_smartphone.png",
    "product_shoes (EXPECTED=REAL)":       "data/product_images/product_shoes.png",
    "fraud_cracked_screen (EXPECTED=FAKE)":"data/fraud_images/fraud_cracked_screen.png",
    "fraud_broken_item (EXPECTED=FAKE)":   "data/fraud_images/fraud_broken_item.png",
    "fraud_reused_shoe (EXPECTED=FAKE)":   "data/fraud_images/fraud_reused_shoe.png",
}

print(f"{'Image':<40} {'AI':>6} {'Foren':>6} {'Final':>6}  {'Verdict':<12} {'OK?'}")
print("-" * 85)
correct = 0
total = len(images)

for name, path in images.items():
    raw = Path(path).read_bytes()
    ela_s, ela_img, ela_gray, orig = compute_ela(raw)
    box_count, _ = compute_contours(ela_gray)
    ratio = compute_anomaly_ratio(ela_gray)
    foren = forensic_score_from_ela(ela_s, box_count, ratio)
    ai_s, ai_ok = detect_ai(raw)
    fs = final_score(ai_s, foren, ai_ok)
    v = verdict(fs, ai_s, foren, ai_ok)
    expected_fraud = "FAKE" in name
    got_fraud = v in ("AI-ALTERED", "REVIEW")
    is_correct = (expected_fraud == got_fraud)
    if is_correct:
        correct += 1
    ok_str = "PASS" if is_correct else "FAIL <<<<<"
    print(f"{name:<40} {ai_s:>6.1f} {foren:>6.1f} {fs:>6.1f}  {v:<12} {ok_str}")

print("-" * 85)
print(f"Accuracy: {correct}/{total} = {correct/total*100:.0f}%")
