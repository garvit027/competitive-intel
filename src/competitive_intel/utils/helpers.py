"""Helper functions for Competitive Intelligence Platform."""

import re
import unicodedata
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            return "unknown"
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"


def parse_date_string(date_str: str) -> datetime | None:
    """Parse various date string formats."""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts."""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """Sanitize string for use as filename."""
    # Normalize unicode
    filename = unicodedata.normalize("NFKD", filename)
    # Remove non-ASCII
    filename = filename.encode("ascii", "ignore").decode("ascii")
    # Replace invalid chars
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    # Collapse whitespace
    filename = re.sub(r"\s+", "_", filename)
    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")
    # Truncate
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename or "unnamed"


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """Extract keywords from text using simple frequency analysis."""
    # Simple stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "can", "this", "that",
        "these", "those", "i", "you", "he", "she", "it", "we", "they",
        "my", "your", "his", "her", "its", "our", "their",
    }

    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    word_freq: dict[str, int] = {}

    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency
    sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
    return [word for word, _ in sorted_words[:max_keywords]]


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    # Remove common suffixes
    suffixes = [
        r"\b(inc|llc|ltd|corp|corporation|company|co|group|holdings|technologies|tech|systems|solutions)\.?\b",
        r"\b(ai|ml|io|app|dev|lab|labs|studio|ventures|capital|partners)\.?\b",
    ]
    normalized = name.lower()
    for suffix in suffixes:
        normalized = re.sub(suffix, "", normalized, flags=re.IGNORECASE)
    # Remove punctuation and extra spaces
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def calculate_signal_similarity(signal1: Any, signal2: Any) -> float:
    """Calculate similarity between two signals."""
    # Compare titles
    title_sim = calculate_text_similarity(
        getattr(signal1, "title", ""),
        getattr(signal2, "title", ""),
    )
    # Compare summaries
    summary_sim = calculate_text_similarity(
        getattr(signal1, "summary", ""),
        getattr(signal2, "summary", ""),
    )
    # Weighted average
    return 0.6 * title_sim + 0.4 * summary_sim


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount."""
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    else:
        return f"${amount:,.0f}"


def parse_funding_amount(text: str) -> float | None:
    """Extract funding amount from text."""
    patterns = [
        r"\$(\d+(?:\.\d+)?)\s*[BM]",
        r"(\d+(?:\.\d+)?)\s*(?:billion|million)",
        r"raised\s+\$?(\d+(?:\.\d+)?)\s*[BM]?",
        r"funding\s+(?:of\s+)?\$?(\d+(?:\.\d+)?)\s*[BM]?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if "billion" in match.group(0).lower() or "b" in match.group(0).lower():
                return value * 1_000_000_000
            elif "million" in match.group(0).lower() or "m" in match.group(0).lower():
                return value * 1_000_000
            return value
    return None


def chunk_text(text: str, max_chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def merge_dicts(*dicts: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple dictionaries, later values override earlier."""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def safe_get(obj: Any, path: str, default: Any = None) -> Any:
    """Safely get nested attribute/dictionary value."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return default
    return current