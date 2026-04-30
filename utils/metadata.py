"""
utils/metadata.py
─────────────────
Extract file metadata and EXIF from image bytes.
"""
import io
from datetime import datetime
from PIL import Image, ExifTags


def extract_metadata(file_bytes: bytes, filename: str = "upload") -> dict:
    """
    Extract metadata from image bytes.

    Returns
    -------
    dict with: size, timestamp, width, height, format, has_exif,
               camera_make, camera_model, software, datetime_original
    """
    meta = {
        "filename":          filename,
        "size":              len(file_bytes),
        "size_kb":           round(len(file_bytes) / 1024, 2),
        "timestamp":         str(datetime.now()),
        "width":             None,
        "height":            None,
        "format":            "Unknown",
        "has_exif":          False,
        "camera_make":       "N/A",
        "camera_model":      "N/A",
        "software":          "N/A",
        "datetime_original": "N/A",
    }
    try:
        img = Image.open(io.BytesIO(file_bytes))
        meta["width"]  = img.width
        meta["height"] = img.height
        meta["format"] = img.format or "Unknown"

        raw_exif = None
        try:
            raw_exif = img._getexif()  # type: ignore
        except Exception:
            pass

        if raw_exif:
            meta["has_exif"] = True
            exif = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}
            meta["camera_make"]       = str(exif.get("Make", "N/A"))
            meta["camera_model"]      = str(exif.get("Model", "N/A"))
            meta["software"]          = str(exif.get("Software", "N/A"))
            meta["datetime_original"] = str(exif.get("DateTimeOriginal",
                                            exif.get("DateTime", "N/A")))
    except Exception:
        pass
    return meta
