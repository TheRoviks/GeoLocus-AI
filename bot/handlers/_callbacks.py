from __future__ import annotations


def parse_callback_id(data: str | None, prefix: str) -> int | None:
    """Extract trailing int from callback_data like ``prefix:123``.

    Returns ``None`` if data is missing, malformed, or not an int.
    """
    if not data or not data.startswith(prefix):
        return None
    tail = data[len(prefix):]
    try:
        return int(tail)
    except ValueError:
        return None
