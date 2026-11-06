import re

_YEAR_RE  = re.compile(r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?', re.IGNORECASE)
_MAX_YEARS = 2


def max_years_in_text(text):
    """Return the highest year number found in text after stripping HTML, or 0 if none."""
    cleaned = re.sub(r'<[^>]+>', ' ', text or '')
    nums = [int(n) for n in _YEAR_RE.findall(cleaned)]
    return max(nums) if nums else 0


def is_entry_level_experience(*texts):
    """Return True if all provided text fields together indicate ≤2 years experience.

    Accepts one or more text strings (e.g. basic_qualifications + description).
    Rule: take the maximum year number found across all fields.
      - 0 found  → include (no explicit year requirement)
      - 1-2 found → include
      - 3+  found → exclude
    """
    combined_max = max((max_years_in_text(t) for t in texts), default=0)
    return combined_max == 0 or combined_max <= _MAX_YEARS
