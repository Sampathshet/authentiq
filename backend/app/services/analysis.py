import io

from PIL import Image, UnidentifiedImageError

from app.storage.files import read_decrypted

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".sol", ".circom", ".sql", ".html", ".css"}


def dhash_bytes(data: bytes) -> str | None:
    try:
        image = Image.open(io.BytesIO(data)).convert("L").resize((9, 8))
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    pixels = list(image.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return format(bits, "016x")


def extract_text(data: bytes, extension: str) -> str | None:
    if extension.lower() not in TEXT_EXTENSIONS:
        return None
    try:
        return data[:500000].decode("utf-8", errors="ignore")
    except Exception:
        return None


def hamming_similarity(left: str, right: str) -> float:
    left_int = int(left, 16)
    right_int = int(right, 16)
    distance = (left_int ^ right_int).bit_count()
    return round(1 - (distance / 64), 4)


def text_similarity(left: str, right: str) -> float:
    def shingles(value: str) -> set[str]:
        words = [w for w in value.lower().split() if w]
        if len(words) < 4:
            return set(words)
        return {" ".join(words[i:i + 4]) for i in range(len(words) - 3)}

    left_set = shingles(left)
    right_set = shingles(right)
    if not left_set or not right_set:
        return 0.0
    intersection = len(left_set & right_set)
    union = len(left_set | right_set)
    return round(intersection / union, 4)


def analyze_duplicates(registration, metadata, candidates, file_bytes: bytes | None = None) -> list[dict]:
    results = []
    extension = metadata.extension if metadata else ""
    perceptual = metadata.perceptual_hash if metadata else None
    text = metadata.extracted_text if metadata else None
    if file_bytes is not None and perceptual is None:
        perceptual = dhash_bytes(file_bytes)
    for candidate, candidate_meta in candidates:
        if candidate.id == registration.id:
            continue
        if candidate.sha256 == registration.sha256:
            results.append({
                "registration": candidate,
                "method": "exact_sha256",
                "score": 1.0,
                "details": {"note": "Byte-identical fingerprint"},
            })
            continue
        if perceptual and candidate_meta and candidate_meta.perceptual_hash:
            score = hamming_similarity(perceptual, candidate_meta.perceptual_hash)
            if score >= 0.90:
                results.append({
                    "registration": candidate,
                    "method": "perceptual_hash",
                    "score": score,
                    "details": {"note": "Perceptual image similarity indicator", "algorithm": "dHash-64"},
                })
        if text and candidate_meta and candidate_meta.extracted_text:
            score = text_similarity(text, candidate_meta.extracted_text)
            if score >= 0.72:
                results.append({
                    "registration": candidate,
                    "method": "text_shingle_jaccard",
                    "score": score,
                    "details": {"note": "Text similarity indicator", "shingle_size": 4},
                })
    results.sort(key=lambda item: item["score"], reverse=True)
    return results


def build_ai_analysis(registration, metadata) -> dict:
    extension = (metadata.extension if metadata else "").lower()
    mime = registration.mime_type or ""
    if mime.startswith("image/") or extension in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        try:
            data = read_decrypted(__import__("pathlib").Path(registration.storage_path))
            image = Image.open(io.BytesIO(data))
            metadata_found = {}
            exif = image.getexif()
            if exif:
                for tag, value in exif.items():
                    metadata_found[str(tag)] = str(value)[:200]
            png_info = getattr(image, "info", {}) or {}
            for key, value in png_info.items():
                if isinstance(value, str):
                    metadata_found[key] = value[:200]
                elif isinstance(value, bytes):
                    metadata_found[key] = value[:200].decode("utf-8", errors="ignore")
            joined = " ".join(str(v) for v in metadata_found.values()).lower()
            known_generators = ["midjourney", "dall-e", "stable diffusion", "firefly", "comfyui", "automatic1111", "novelai"]
            signals = [name for name in known_generators if name in joined]
            c2pa_present = any("c2pa" in str(k).lower() or "c2pa" in str(v).lower() for k, v in metadata_found.items())
            return {
                "analysis_available": True,
                "method": "image_metadata_inspection",
                "metadata_fields": metadata_found,
                "generator_signals": signals,
                "c2pa_manifest_present": c2pa_present,
                "signal_strength": "metadata-only",
                "confidence": "low" if signals or c2pa_present else "none",
                "limitations": "Absence or presence of generator metadata is not conclusive. Metadata can be removed or forged. No ML classifier is configured.",
                "model_configured": False,
            }
        except Exception as exc:
            return {
                "analysis_available": False,
                "method": "image_metadata_inspection",
                "reason": f"Metadata could not be read: {exc}",
                "limitations": "No detection result is reported when the file cannot be inspected.",
            }
    if mime == "application/pdf" or extension == ".pdf":
        try:
            data = read_decrypted(__import__("pathlib").Path(registration.storage_path))[:5_000_000]
            text = data.decode("latin-1", errors="ignore")
            markers = {}
            for marker in ["/Producer", "/Creator", "/CreationDate", "C2PA", "Midjourney", "OpenAI", "Adobe Firefly", "Stable Diffusion"]:
                if marker.lower() in text.lower():
                    markers[marker] = True
            return {
                "analysis_available": True,
                "method": "pdf_metadata_scan",
                "metadata_fields": markers,
                "generator_signals": [m for m in markers if m in {"Midjourney", "OpenAI", "Adobe Firefly", "Stable Diffusion"}],
                "c2pa_manifest_present": bool(markers.get("C2PA")),
                "signal_strength": "metadata-only",
                "confidence": "low",
                "limitations": "PDF metadata is user-editable and cannot conclusively prove AI or human origin.",
                "model_configured": False,
            }
        except Exception as exc:
            return {
                "analysis_available": False,
                "method": "pdf_metadata_scan",
                "reason": str(exc),
                "limitations": "No detection result is reported when the file cannot be inspected.",
            }
    return {
        "analysis_available": False,
        "method": "none",
        "reason": "No detection model or metadata analyzer is configured for this file type.",
        "limitations": "AUTHENTIQ does not fabricate AI detection results. Add a classifier to enable probabilistic analysis.",
        "model_configured": False,
    }
