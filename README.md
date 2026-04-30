# 🛡️ Return Fraud Intelligence System

AI-powered real-time fraud detection for return/refund claims.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Structure

```
backup/
├── app.py                    # Main Streamlit app (multi-page)
├── requirements.txt
├── model/
│   ├── image_similarity.py   # CLIP-based cosine similarity
│   ├── metadata_check.py     # EXIF analysis
│   └── scoring.py            # Fraud scoring engine
└── data/
    ├── users.json            # User behavior profiles
    ├── product_images/       # Reference product photos
    └── fraud_images/         # Known fraud/reused images
```

## Scoring Engine

| Signal             | Max Points |
|--------------------|-----------|
| Image Similarity   | 50        |
| Metadata Analysis  | 20        |
| User Behaviour     | 30        |
| **Total**          | **100**   |

| Score    | Risk Level  | Decision               |
|----------|-------------|------------------------|
| 0–29     | Low Risk    | Auto Approve           |
| 30–59    | Medium Risk | Monitor                |
| 60–100   | High Risk   | Send to Manual Review  |

## Note on CLIP

First run downloads `openai/clip-vit-base-patch32` (~350 MB). Cached automatically.
