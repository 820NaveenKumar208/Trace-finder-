"""
VerifyFlow – Real-Time Return & Refund Fraud Detection System
Run: streamlit run app.py
"""
import io, sys, time
from pathlib import Path
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.risk_engine import compute_final_risk, ai_detector
from core.rule_scorer  import get_all_hashes
from blockchain.web3_handler import log_to_blockchain

st.set_page_config(page_title="VerifyFlow", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#0E1117;}
.block-container{padding-top:1rem;}
section[data-testid="stSidebar"]{background:#0a0f1a;border-right:1px solid #00FFAA22;}
.stButton>button{background:linear-gradient(135deg,#00FFAA,#00C87A);color:#0E1117!important;
  border:none;border-radius:10px;font-weight:800;transition:all .2s;}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 0 20px #00FFAA44;}
[data-testid="stMetric"]{background:#1E1E2E;border:1px solid #00FFAA22;border-radius:12px;padding:14px!important;}
[data-testid="stMetricValue"]{color:#F0F0F0!important;font-weight:700;}
[data-testid="stMetricLabel"]{color:#8888AA!important;font-size:.78rem;}
h1{color:#00FFAA!important;} h2,h3{color:#E0E0E0!important;}
.stProgress>div>div>div>div{background:linear-gradient(90deg,#00FFAA,#00C87A)!important;}
</style>""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='text-align:center;padding:14px 0 6px;'>
      <div style='font-size:1.8rem;'>🛡️</div>
      <div style='font-size:1.1rem;font-weight:900;color:#00FFAA;letter-spacing:2px;'>VerifyFlow</div>
      <div style='font-size:.68rem;color:#5A5A7A;'>Return Fraud Detection</div>
    </div>""", unsafe_allow_html=True)
    st.divider()
    page = st.radio("Nav", ["🏠 Home","🔍 Analyze","📊 Dashboard","📖 About"],
                    label_visibility="collapsed")
    st.divider()
    ai_status = "🟢 Online" if ai_detector.available else "🔴 Offline"
    model_name = (ai_detector.model_name or "N/A").split("/")[-1]
    st.markdown(f"""<div style='font-size:.72rem;color:#5A5A7A;line-height:2;text-align:center;'>
      🤖 AI Model: <b style='color:#00FFAA;'>{ai_status}</b><br>
      <span style='font-size:.65rem;'>{model_name}</span><br>
      ⛓️ Blockchain gate: risk &gt; 70
    </div>""", unsafe_allow_html=True)

# ═══════════════════ HOME ════════════════════════════════════
if page == "🏠 Home":
    st.markdown("""<div style='text-align:center;padding:40px 0 24px;'>
      <div style='font-size:3rem;'>🛡️</div>
      <h1 style='font-size:2.4rem;font-weight:900;margin:8px 0;'>VerifyFlow</h1>
      <p style='color:#8888AA;font-size:1rem;'>
        Real-Time Return &amp; Refund Fraud Detection<br>
        <b style='color:#00FFAA;'>AI · Rules · Blockchain</b>
      </p></div>""", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    for col,n,ic,t,d in [
      (c1,"1","🤖","AI Detection","HuggingFace model classifies Real vs AI-generated (60% weight)"),
      (c2,"2","📋","Rule Engine","Hash + EXIF + size + frequency scoring (40% weight)"),
      (c3,"3","⛓️","Blockchain","Tamper-proof audit log — only for FRAUD (score > 70)"),
    ]:
        col.markdown(f"""<div style='background:#1E1E2E;border:1px solid #00FFAA22;
          border-radius:14px;padding:20px;text-align:center;min-height:160px;'>
          <div style='background:#00FFAA;color:#0E1117;border-radius:50%;width:28px;height:28px;
            display:inline-flex;align-items:center;justify-content:center;
            font-weight:900;font-size:.82rem;margin-bottom:8px;'>{n}</div>
          <div style='font-size:1.4rem;'>{ic}</div>
          <div style='font-weight:700;color:#F0F0F0;font-size:.88rem;margin:6px 0 4px;'>{t}</div>
          <div style='color:#8888AA;font-size:.78rem;line-height:1.5;'>{d}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    v1,v2,v3 = st.columns(3)
    for col,clr,lbl,rng in [
      (v1,"#22C55E","✅ REAL","final ≤ 35"),
      (v2,"#F59E0B","⚠️ REVIEW","35 < final ≤ 70"),
      (v3,"#EF4444","🚫 FRAUD","final > 70  → blockchain"),
    ]:
        col.markdown(f"""<div style='background:#1E1E2E;border-left:4px solid {clr};
          border-radius:10px;padding:14px;text-align:center;'>
          <div style='color:{clr};font-weight:900;'>{lbl}</div>
          <div style='color:#8888AA;font-size:.78rem;'>{rng}</div>
        </div>""", unsafe_allow_html=True)

# ═══════════════════ ANALYZE ══════════════════════════════════
elif page == "🔍 Analyze":
    st.markdown("<h1 style='font-size:1.8rem;font-weight:900;margin:0 0 4px;'>🔍 Fraud Analysis</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='color:#8888AA;font-size:.86rem;margin:0 0 14px;'>Upload a product return image · 3-layer pipeline runs instantly</p>",
                unsafe_allow_html=True)

    with st.form("fraud_form"):
        cu, ci = st.columns([2,1])
        with cu:
            uploaded = st.file_uploader("📤 Upload product image",
                                        type=["jpg","jpeg","png","webp"])
        with ci:
            claim_id = st.text_input("🔖 Claim ID", placeholder="CLM-2024-001")
            claimant = st.text_input("👤 Claimant",  placeholder="John Doe")
        run = st.form_submit_button("🔍 Run Fraud Check", use_container_width=True)

    if not run:
        st.markdown("""<div style='text-align:center;padding:50px;color:#3A3A5A;'>
          <div style='font-size:3.5rem;'>🛡️</div>
          <p style='margin-top:10px;'>Upload an image and click <b style='color:#00FFAA;'>Run Fraud Check</b></p>
        </div>""", unsafe_allow_html=True)
        st.stop()

    if not uploaded:
        st.error("⚠️ Please upload an image."); st.stop()

    file_bytes = uploaded.read()

    # ── Run pipeline ──────────────────────────────────────────
    with st.spinner("🔄 Running 3-layer fraud detection pipeline…"):
        t0     = time.perf_counter()
        result = compute_final_risk(file_bytes, uploaded.name)
        elapsed = round(time.perf_counter() - t0, 2)

    ai_score      = result['ai_score']
    ai_confidence = result['ai_confidence']
    ai_label      = result['ai_label']
    rule_score    = result['rule_score']
    final         = result['final_score']
    verdict       = result['verdict']
    reasons       = result['reasons']
    metadata      = result['metadata']
    image_hash    = result['image_hash']
    sys_conf      = result['system_confidence']
    conf_label    = result['confidence_label']

    COLORS = {"REAL":"#22C55E","REVIEW":"#F59E0B","FRAUD":"#EF4444"}
    EMOJIS = {"REAL":"✅","REVIEW":"⚠️","FRAUD":"🚫"}
    clr    = COLORS[verdict]
    emo    = EMOJIS[verdict]
    CONF_COLORS = {"HIGH":"#22C55E","MEDIUM":"#F59E0B","LOW":"#EF4444"}
    conf_clr = CONF_COLORS[conf_label]

    # ── Score cards + System Confidence ─────────────────────────────
    s1,s2,s3,s4 = st.columns(4)
    if ai_score is not None:
        s1.metric("🤖 AI Score",   f"{ai_score}/100",   help="60% weight")
    else:
        s1.metric("🤖 AI Score", "Offline", help="Model unavailable")
    s2.metric("📋 Rule Score", f"{rule_score}/100", help="40% weight")
    s3.metric("🔍 Final Risk", f"{final}/100")
    # Improvement 4: Decision Confidence = 100 - abs(ai_score - rule_score)
    if ai_score is not None:
        dec_conf = round(100 - abs(ai_score - rule_score), 1)
    else:
        dec_conf = round(100 - abs(rule_score - 50), 1)
    dec_conf = min(100.0, max(0.0, dec_conf))
    if dec_conf >= 75:   dec_label, dec_clr = "HIGH",   "#22C55E"
    elif dec_conf >= 45: dec_label, dec_clr = "MEDIUM", "#F59E0B"
    else:                dec_label, dec_clr = "LOW",    "#EF4444"
    dec_phrase = {
        "HIGH":   "consistent signals",
        "MEDIUM": "mixed signals",
        "LOW":    "conflicting signals",
    }[dec_label]

    s4.markdown(f"""
    <div style='background:#1E1E2E;border:1px solid {dec_clr}44;border-radius:12px;
      padding:14px;text-align:center;'>
      <div style='color:#8888AA;font-size:.76rem;margin-bottom:4px;'>🧠 Decision Confidence</div>
      <div style='font-weight:900;font-size:1.05rem;color:{dec_clr};'>{dec_label} ({dec_conf:.0f}%)</div>
      <div style='font-size:.68rem;color:#5A5A7A;margin-top:3px;font-style:italic;'>{dec_phrase}</div>
    </div>""", unsafe_allow_html=True)

    # Progress bar
    st.progress(int(final))

    # Improvement 5: Severity badge + verdict
    SEV   = {"REAL":"LOW","REVIEW":"MEDIUM","FRAUD":"HIGH"}
    sev   = SEV[verdict]
    pulse = "animation:pulse 1.6s infinite;" if verdict == "FRAUD" else ""
    st.markdown(f"""
    <style>@keyframes pulse{{
      0%{{box-shadow:0 0 0 0 {clr}55;}} 70%{{box-shadow:0 0 0 18px {clr}00;}} 100%{{box-shadow:0 0 0 0 {clr}00;}}
    }}</style>
    <div style='background:{clr}12;border:2px solid {clr};border-radius:16px;
      padding:22px;text-align:center;margin:14px 0;{pulse}'>
      <div style='display:flex;justify-content:center;gap:16px;margin-bottom:8px;'>
        <span style='background:{clr}22;color:{clr};border-radius:20px;padding:3px 14px;
          font-size:.72rem;font-weight:700;letter-spacing:.1em;border:1px solid {clr}55;'>
          ⚖️ VERDICT</span>
        <span style='background:{clr}22;color:{clr};border-radius:20px;padding:3px 14px;
          font-size:.72rem;font-weight:700;letter-spacing:.1em;border:1px solid {clr}55;'>
          🎯 SEVERITY: {sev}</span>
      </div>
      <div style='font-size:2.4rem;font-weight:900;color:{clr};'>{emo} {verdict}</div>
      <div style='color:#8888AA;font-size:.8rem;margin-top:6px;'>
        Final Risk Score: <b style='color:{clr};font-size:1.4rem;'>{final}</b>/100
        &nbsp;·&nbsp; ⚡ {elapsed}s
      </div>
    </div>""", unsafe_allow_html=True)

    # WOW Feature: Risk Breakdown Bar
    ai_contrib   = round(0.6 * (ai_score or 0), 1)
    rule_contrib = round(0.4 * rule_score, 1)
    st.markdown(f"""
    <div style='background:#1A1A2A;border-radius:12px;padding:14px 18px;margin-bottom:12px;'>
      <div style='font-size:.7rem;font-weight:700;color:#00FFAA;
        letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;'>📊 Risk Breakdown</div>
      <div style='display:flex;align-items:center;gap:8px;font-size:.82rem;color:#8888AA;'>
        <span>🤖 AI</span>
        <div style='flex:1;background:#2A2A3A;border-radius:4px;height:8px;'>
          <div style='width:{min(100,ai_score or 0):.0f}%;background:#7C3AED;height:8px;border-radius:4px;'></div>
        </div>
        <span style='color:#7C3AED;font-weight:700;min-width:32px;'>{ai_contrib}</span>
        <span style='color:#3A3A5A;'>|</span>
        <span>📋 Rules</span>
        <div style='flex:1;background:#2A2A3A;border-radius:4px;height:8px;'>
          <div style='width:{min(100,rule_score):.0f}%;background:#F59E0B;height:8px;border-radius:4px;'></div>
        </div>
        <span style='color:#F59E0B;font-weight:700;min-width:32px;'>{rule_contrib}</span>
        <span style='color:#3A3A5A;'>→</span>
        <span>Final</span>
        <span style='color:{clr};font-weight:900;font-size:.92rem;'>{final}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Main layout ────────────────────────────────────────────
    left, right = st.columns([1,1], gap="large")
    with left:
        # Improvement 3: Full model credibility card with inference time
        model_full  = ai_detector.model_name or "N/A"
        model_short = model_full.split("/")[-1]
        # Map label to human-readable prediction
        label_map = {
            "real":"HUMAN / REAL", "human":"HUMAN / REAL",
            "authentic":"HUMAN / REAL", "original":"HUMAN / REAL",
            "ai":"AI-GENERATED", "ai-generated":"AI-GENERATED",
            "fake":"AI-GENERATED", "artificial":"AI-GENERATED",
        }
        ai_pred_label = label_map.get(ai_label.lower(), ai_label.upper())
        ai_conf_disp  = f"{ai_confidence:.0f}%" if result['ai_model_available'] else "N/A"
        pred_clr      = "#22C55E" if "HUMAN" in ai_pred_label else ("#EF4444" if "AI" in ai_pred_label else "#F59E0B")
        st.markdown(f"""
        <div style='background:#1A1A2A;border:1px solid #00FFAA22;border-radius:12px;
          padding:14px 18px;margin-bottom:12px;'>
          <div style='font-size:.7rem;font-weight:700;color:#00FFAA;
            letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;'>🤖 AI Model Analysis</div>
          <div style='font-size:.82rem;color:#8888AA;line-height:2.2;'>
            <span style='color:#5A5A7A;'>Model:</span>
            <b style='color:#E0E0E0;font-size:.78rem;'> {model_full}</b><br>
            <span style='color:#5A5A7A;'>Prediction:</span>
            <b style='color:{pred_clr};'> {ai_pred_label}</b><br>
            <span style='color:#5A5A7A;'>Confidence:</span>
            <b style='color:{pred_clr};'> {ai_conf_disp}</b><br>
            <span style='color:#5A5A7A;'>Inference time:</span>
            <b style='color:#E0E0E0;'> {elapsed}s</b>
          </div>
        </div>""", unsafe_allow_html=True)

        # Detection Signals
        st.markdown("<h3 style='font-size:.88rem;color:#00FFAA;text-transform:uppercase;letter-spacing:.1em;margin:0 0 8px;'>📝 Detection Signals</h3>",
                    unsafe_allow_html=True)
        # Remove AI line from reasons (shown in card above)
        sig_reasons = [r for r in reasons if not r.startswith("🤖")]
        st.markdown(
            "<div style='background:#1A1A2A;border-radius:12px;padding:14px 18px;'>" +
            "".join(f"<p style='margin:5px 0;color:#D0D0E0;font-size:.88rem;'>{r}</p>" for r in sig_reasons) +
            "</div>", unsafe_allow_html=True)

        # Improvement 2: Contextual Why VERDICT? checklist
        is_dup   = any("Duplicate" in r for r in reasons)
        has_exif = metadata["has_exif"]
        size_ok  = metadata["size"] >= 5000
        ai_ok    = ai_score is not None and ai_score < 40
        # (is_good, good_label, bad_label)
        why_items = [
            (
                not is_dup,
                "No duplicate image detected",
                "⚠️ Duplicate detected — but check AI confidence for full context",
            ),
            (
                ai_ok,
                f"AI model strongly indicates real content ({ai_confidence:.0f}% confidence)",
                f"⚠️ AI model flagged as generated — {ai_confidence:.0f}% confidence",
            ),
            (
                has_exif,
                "File metadata present and within normal range",
                "⚠️ EXIF missing (common for screenshots or web images)",
            ),
            (
                size_ok,
                "File size looks legitimate",
                "⚠️ File size suspiciously small — may be a placeholder",
            ),
        ]
        st.markdown(f"""
        <div style='background:#1A1A2A;border:1px solid #00FFAA22;border-radius:12px;
          padding:14px 18px;margin-top:10px;'>
          <div style='font-size:.7rem;font-weight:700;color:#00FFAA;
            letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;'>
            ❓ Why {verdict}?
          </div>""" +
        "".join(
            f"<p style='margin:5px 0;font-size:.84rem;color:{'#22C55E' if ok else '#F59E0B'};'>"
            f"{'✔' if ok else '⚠️'} {good if ok else bad}</p>"
            for ok, good, bad in why_items
        ) + "</div>", unsafe_allow_html=True)

        # Image preview
        st.markdown("<br>", unsafe_allow_html=True)
        st.image(Image.open(io.BytesIO(file_bytes)), caption=uploaded.name,
                 use_container_width=True)

    with right:
        # Metadata
        st.markdown("<h3 style='font-size:.88rem;color:#00FFAA;text-transform:uppercase;letter-spacing:.1em;margin:0 0 8px;'>📋 Metadata</h3>",
                    unsafe_allow_html=True)
        st.markdown(f"""<div style='background:#1A1A2A;border-radius:12px;padding:14px 18px;
          font-size:.8rem;color:#8888AA;line-height:2;'>
          📄 <b style='color:#E0E0E0;'>{uploaded.name}</b><br>
          📦 Size: <b style='color:#E0E0E0;'>{metadata['size_kb']:.1f} KB</b> ({metadata['size']} bytes)<br>
          🖼️ Dimensions: <b style='color:#E0E0E0;'>{metadata['width']} × {metadata['height']}</b><br>
          📋 EXIF: <b style='color:{"#22C55E" if metadata["has_exif"] else "#EF4444"};'>
            {"Present ✅" if metadata["has_exif"] else "Missing ⚠️"}</b><br>
          📷 Camera: <b style='color:#E0E0E0;'>{metadata['camera_make']} {metadata['camera_model']}</b><br>
          🔐 Hash: <span style='font-family:monospace;font-size:.72rem;color:#5A5A7A;'>
            {image_hash[:40]}…</span>
        </div>""", unsafe_allow_html=True)

        # Improvement 6: Blockchain storytelling
        st.markdown("<br>", unsafe_allow_html=True)
        if verdict == "FRAUD" and final > 70:
            with st.spinner("⛓️ Logging fraud evidence to blockchain…"):
                bc = log_to_blockchain(image_hash, int(final))
            clr_bc = "#F59E0B" if bc["simulated"] else "#00FFAA"
            badge  = "🔶 Simulated" if bc["simulated"] else "✅ On-Chain"
            tx_short = bc['tx_hash'][:10] + "…"
            st.markdown(f"""
            <div style='background:#1E1E2E;border:2px solid {clr_bc};border-radius:12px;
              padding:14px 18px;'>
              <div style='font-size:.7rem;font-weight:700;color:{clr_bc};
                letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;'>
                ⛓️ BLOCKCHAIN: EVIDENCE SEALED {badge}
              </div>
              <div style='font-size:.78rem;color:#8888AA;line-height:2.2;'>
                🔗 Logged: <span style='color:{clr_bc};font-family:monospace;'>
                  {tx_short}</span>
                <span style='color:#3A3A5A;font-size:.72rem;'> (click to copy full TX)</span><br>
                <span style='font-family:monospace;font-size:.7rem;color:#5A5A7A;
                  word-break:break-all;'>{bc['tx_hash']}</span>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            score_needed = max(0, 70 - final)
            st.markdown(f"""
            <div style='background:#1A1A2A;border:2px solid #2A2A3A;border-radius:12px;
              padding:14px 18px;'>
              <div style='display:flex;align-items:flex-start;gap:12px;'>
                <span style='font-size:1.4rem;margin-top:2px;'>⛓️</span>
                <div>
                  <div style='font-size:.7rem;font-weight:700;color:#5A5A7A;
                    letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px;'>BLOCKCHAIN</div>
                  <div style='color:#8888AA;font-size:.82rem;'>
                    Blockchain logging is triggered only for high-risk cases (&gt;70)
                  </div>
                  <div style='color:#5A5A7A;font-size:.74rem;margin-top:4px;'>
                    Current score: <b style='color:#E0E0E0;'>{final}</b> — needs
                    <b style='color:#F59E0B;'>+{score_needed:.0f}</b> more points to trigger
                  </div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

# ═══════════════════ DASHBOARD ════════════════════════════════
elif page == "📊 Dashboard":
    import pandas as pd
    from datetime import datetime

    store = get_all_hashes()
    st.markdown("## 📊 Audit Dashboard")
    st.divider()

    total     = len(store)
    dups      = sum(1 for v in store.values() if v["count"] > 1)
    total_sub = sum(v["count"] for v in store.values())
    dup_rate  = dups / total * 100 if total else 0.0

    d1,d2,d3,d4 = st.columns(4)
    d1.metric("🖼️ Unique Images",    total)
    d2.metric("🔁 Duplicate Images", dups)
    d3.metric("📥 Total Submitted",  total_sub)
    d4.metric("⚠️ Duplicate Rate",   f"{dup_rate:.0f}%")

    if not store:
        st.info("No images analyzed yet. Go to 🔍 Analyze."); st.stop()

    rows_raw = list(store.items())

    # Fraud Insights
    hours = []
    for _, v in rows_raw:
        last = v.get("last_seen","")
        if last:
            try: hours.append(datetime.fromisoformat(last).strftime("%H:%M"))
            except: pass
    peak_time    = max(set(hours), key=hours.count) if hours else "N/A"
    most_rep     = max(rows_raw, key=lambda x: x[1]["count"])
    most_hash    = most_rep[0][:16] + "…"
    most_count   = most_rep[1]["count"]

    # Trend
    now = datetime.utcnow()
    r30, p30 = 0, 0
    for _, v in rows_raw:
        last = v.get("last_seen","")
        if last:
            try:
                s = (now - datetime.fromisoformat(last)).total_seconds()
                if s < 30: r30 += 1
                elif s < 60: p30 += 1
            except: pass
    if r30 > p30:   ti,tl,tc = "📈","Increasing","#EF4444"
    elif r30 < p30: ti,tl,tc = "📉","Decreasing","#22C55E"
    else:           ti,tl,tc = "➡️","Stable","#F59E0B"

    ic, tc_col = st.columns([2,1])
    with ic:
        st.markdown(f"""<div style='background:#1E1E2E;border:1px solid #00FFAA33;
          border-radius:14px;padding:18px 22px;margin:12px 0;'>
          <div style='font-size:.7rem;font-weight:700;color:#00FFAA;
            letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px;'>🔥 Fraud Insights</div>
          <p style='margin:5px 0;color:#D0D0E0;font-size:.86rem;'>
            • <b>{dups}</b> duplicate image(s) detected</p>
          <p style='margin:5px 0;color:#D0D0E0;font-size:.86rem;'>
            • Most repeated: <span style='color:#F59E0B;font-family:monospace;'>{most_hash}</span>
            — <b style='color:#EF4444;'>{most_count}×</b></p>
          <p style='margin:5px 0;color:#D0D0E0;font-size:.86rem;'>
            • Peak fraud time: <b style='color:#00FFAA;'>{peak_time}</b></p>
          <p style='margin:5px 0;color:#D0D0E0;font-size:.86rem;'>
            • Duplicate rate: <b style='color:{"#EF4444" if dup_rate>30 else "#22C55E"};'>
              {dup_rate:.1f}%</b>
            {'⚠️ HIGH' if dup_rate > 30 else '✅ Normal'}</p>
        </div>""", unsafe_allow_html=True)
    with tc_col:
        st.markdown(f"""<div style='background:#1E1E2E;border:1px solid {tc}44;
          border-radius:14px;padding:18px;margin:12px 0;text-align:center;'>
          <div style='font-size:.7rem;font-weight:700;color:{tc};
            letter-spacing:.12em;text-transform:uppercase;'>📡 Fraud Trend</div>
          <div style='font-size:2rem;margin:8px 0;'>{ti}</div>
          <div style='font-size:1.1rem;font-weight:900;color:{tc};'>{tl}</div>
          <div style='color:#5A5A7A;font-size:.7rem;margin-top:4px;'>Last 60s</div>
        </div>""", unsafe_allow_html=True)

    # Table with red fraud rows
    st.markdown("<h3 style='color:#00FFAA;font-size:.88rem;text-transform:uppercase;letter-spacing:.1em;'>🗂️ Submission Log</h3>",
                unsafe_allow_html=True)
    df_rows = []
    for h, v in rows_raw[-20:]:
        fd = v["count"] > 1
        df_rows.append({"Status": "🔴 FRAUD DETECTED" if fd else "✅ CLEAN",
                         "Hash": h[:24]+"…","Submissions":v["count"],
                         "First Seen":v.get("first_seen","–")[:19],
                         "Last Seen":v.get("last_seen","–")[:19],"_fd":fd})
    df = pd.DataFrame(df_rows[::-1])
    disp = df.drop(columns=["_fd"])
    def hi(row):
        return ["background-color:#2D1515;color:#FF6B6B;font-weight:700"]*len(row) \
               if df.loc[row.name,"_fd"] else [""]*len(row)
    st.dataframe(disp.style.apply(hi,axis=1), use_container_width=True, hide_index=True)

    csv = disp.to_csv(index=False).encode("utf-8")
    col_dl, _ = st.columns([1,3])
    with col_dl:
        st.download_button("⬇️ Download Report (CSV)", csv,
            file_name=f"verifyflow_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv", use_container_width=True)

# ═══════════════════ ABOUT ════════════════════════════════════
elif page == "📖 About":
    st.markdown("## 📖 About VerifyFlow")
    st.divider()
    st.markdown("""<div style='background:#1E1E2E;border:1px solid #00FFAA22;
      border-radius:14px;padding:22px;margin-bottom:14px;'>
      <h3 style='color:#00FFAA;font-size:1rem;margin:0 0 8px;'>🎤 Hackathon Pitch</h3>
      <p style='color:#94a3b8;font-style:italic;line-height:1.8;font-size:.95rem;'>
        "VerifyFlow detects fraudulent return claims by combining AI-based image validation,
        metadata intelligence, and blockchain-backed audit trails for tamper-proof verification."
      </p></div>""", unsafe_allow_html=True)

    a1,a2 = st.columns(2,gap="large")
    with a1:
        st.markdown("""<div style='background:#1E1E2E;border:1px solid #00FFAA22;
          border-radius:14px;padding:20px;'>
          <h3 style='color:#00FFAA;font-size:.95rem;margin:0 0 10px;'>⚙️ Scoring Formula</h3>
          <p style='color:#94a3b8;font-family:monospace;font-size:.82rem;line-height:2;'>
            final = 0.6 × AI_score + 0.4 × rule_score<br>
            REAL   → final ≤ 35<br>
            REVIEW → 35 &lt; final ≤ 70<br>
            FRAUD  → final &gt; 70  → blockchain
          </p></div>""", unsafe_allow_html=True)
    with a2:
        st.markdown("""<div style='background:#1E1E2E;border:1px solid #00FFAA22;
          border-radius:14px;padding:20px;'>
          <h3 style='color:#00FFAA;font-size:.95rem;margin:0 0 10px;'>🏗️ Tech Stack</h3>""",
                    unsafe_allow_html=True)
        for t in ["Streamlit","Python 3.11","Transformers 4.46","PyTorch 2.5",
                  "Pillow/EXIF","SHA-256","Web3.py","Solidity/Ganache"]:
            st.markdown(f"<span style='background:#00FFAA18;color:#00FFAA;border-radius:20px;"
                        f"padding:4px 12px;font-size:.78rem;'>{t}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
