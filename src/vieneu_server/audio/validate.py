from __future__ import annotations


def validate_audio_format(format_name: str) -> str:
    normalized = format_name.lower()
    if normalized != "wav":
        raise ValueError("Only wav output is supported.")
    return normalized
