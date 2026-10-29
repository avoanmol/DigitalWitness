"""Privacy-limited metadata observations; never an authenticity verdict."""
from __future__ import annotations

import io
from typing import Any

CAVEAT = "Metadata may be absent, edited, or spoofed. These observations do not establish authenticity."


def inspect_static_provenance(data: bytes, mime_type: str) -> dict[str, Any]:
    mime_type = mime_type.split(";")[0].strip().lower()
    if mime_type in {"image/jpeg", "image/png", "image/webp"}:
        from PIL import Image, ExifTags
        with Image.open(io.BytesIO(data)) as image:
            exif = image.getexif()
            names = {ExifTags.TAGS.get(key, str(key)).casefold() for key in exif.keys()}
            info_names = {str(key).casefold() for key in image.info}
            observations = []
            if names & {"software", "processingsoftware"} or info_names & {"software", "xml:com.adobe.xmp"}:
                observations.append("Software/editing metadata field is present.")
            if names & {"datetime", "datetimeoriginal", "datetimedigitized"} or info_names & {"creation time", "date:create", "date:modify"}:
                observations.append("Creation-time metadata field is present.")
            if "gpsinfo" in names:
                observations.append("GPS metadata field is present; location values are intentionally not collected.")
            return {
                "file_format": image.format or ("JPEG" if mime_type == "image/jpeg" else "PNG"),
                "metadata_present": bool(names or info_names),
                "dimensions": {"width": int(image.width), "height": int(image.height)},
                "observations": observations,
                "caveat": CAVEAT,
            }
    if mime_type == "application/pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=False)
        metadata = reader.metadata or {}
        keys = {str(key).lstrip("/").casefold() for key in metadata.keys()}
        observations = []
        if "producer" in keys:
            observations.append("PDF producer metadata field is present; its value is not retained.")
        if "creator" in keys:
            observations.append("PDF creator metadata field is present; its value is not retained.")
        if keys & {"creationdate", "moddate"}:
            observations.append("PDF date metadata field is present; its value is not treated as a trusted timestamp.")
        return {
            "file_format": "PDF",
            "metadata_present": bool(keys),
            "page_count": len(reader.pages),
            "observations": observations,
            "caveat": CAVEAT,
        }
    return {"file_format": "unknown", "metadata_present": False, "observations": [], "caveat": CAVEAT}
