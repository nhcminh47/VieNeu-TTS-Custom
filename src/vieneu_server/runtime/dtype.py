from __future__ import annotations


def dtype_name(dtype: object) -> str:
    text = str(dtype)
    return text.replace("torch.", "")
