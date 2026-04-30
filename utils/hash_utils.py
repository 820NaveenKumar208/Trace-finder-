"""
utils/hash_utils.py
───────────────────
SHA-256 image hashing + persistent duplicate detection.
Stores history in storage/hashes.json.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

STORAGE_PATH = Path(__file__).resolve().parent.parent / "storage" / "hashes.json"


def generate_hash(file_bytes: bytes) -> str:
    """Return SHA-256 hex digest of raw image bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


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


def check_duplicate(image_hash: str) -> tuple[bool, int]:
    """
    Check if hash was seen before. Registers the hash each time called.

    Returns
    -------
    (is_duplicate, submission_count)
    """
    store = _load_store()
    entry = store.get(image_hash, {"count": 0, "first_seen": None})
    is_duplicate = entry["count"] > 0
    entry["count"] += 1
    entry["last_seen"] = datetime.utcnow().isoformat()
    if not entry["first_seen"]:
        entry["first_seen"] = entry["last_seen"]
    store[image_hash] = entry
    _save_store(store)
    return is_duplicate, entry["count"]


def get_recent_count(window_seconds: int = 60) -> int:
    """Count unique images submitted in the last window_seconds."""
    store = _load_store()
    now = datetime.utcnow()
    count = 0
    for entry in store.values():
        last = entry.get("last_seen")
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
