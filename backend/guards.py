"""Best-effort prompt-injection detection.

Heuristic only — used for logging/observability, never to block (false positives
would reject legitimate job descriptions). The real defense is the hardened
system prompts and input delimiting in prompts.py.
"""
import re

_PATTERNS = [
    # English
    r"ignore\s+(the\s+|all\s+|your\s+|these\s+)?(previous\s+|prior\s+|above\s+)?instructions",
    r"disregard\s+(the\s+|all\s+|your\s+|previous\s+|above\s+)?instructions",
    r"forget\s+(the\s+|all\s+|your\s+|previous\s+)?instructions",
    r"you\s+are\s+now\b",
    r"new\s+instructions?\b",
    r"system\s+prompt",
    # French
    r"ignore[zr]?\s+(les\s+|tes\s+|ces\s+)?(instructions|consignes)",
    r"oublie[zr]?\s+(les\s+|tes\s+)?(instructions|consignes)",
    r"tu\s+es\s+maintenant\b",
    r"nouvelles?\s+instructions?\b",
]

_REGEX = re.compile("|".join(_PATTERNS), re.IGNORECASE)


def looks_like_injection(text: str) -> bool:
    """True if the text contains a known prompt-injection marker."""
    if not text:
        return False
    return bool(_REGEX.search(text))
