"""Optional local OCR helpers for a user-confirmed bet-slip tracking flow."""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any

try:  # Keep the API usable when an operator has not installed OCR dependencies.
    from PIL import Image, UnidentifiedImageError
    import pytesseract
except ImportError:  # pragma: no cover - exercised in deployments without OCR extras.
    Image = None
    UnidentifiedImageError = Exception
    pytesseract = None


MAX_IMAGE_BYTES = 5 * 1024 * 1024


class OCRUnavailable(RuntimeError):
    """Raised when local OCR cannot safely process a submitted image."""


def parse_slip_text(text: str) -> dict[str, Any]:
    """Return conservative suggestions from OCR text; never treat them as confirmed."""

    normalized = " ".join(text.split())
    odds_match = re.search(r"(?<!\d)([+-]\d{2,4})(?!\d)", normalized)
    stake_match = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", normalized)
    return {
        "american_odds": int(odds_match.group(1)) if odds_match else None,
        "stake": float(stake_match.group(1)) if stake_match else None,
        "selection": None,
    }


def extract_bet_slip(image_bytes: bytes) -> dict[str, Any]:
    """OCR an in-memory image without writing the image or OCR text to the database."""

    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise OCRUnavailable("Use an image between 1 byte and 5 MB.")
    if Image is None or pytesseract is None:
        raise OCRUnavailable("Local OCR is not installed. Enter the slip fields manually.")

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        text = pytesseract.image_to_string(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise OCRUnavailable("The uploaded file is not a readable image.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailable("Tesseract is not installed on this server. Enter the fields manually.") from exc

    return {
        "suggestions": parse_slip_text(text),
        "text_preview": text[:1000],
        "requires_confirmation": True,
        "storage": "The image and OCR text are not saved. Only fields you confirm can be tracked locally.",
    }
