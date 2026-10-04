"""Unit tests for utility functions."""

import pytest

from competitive_intel.utils.helpers import (
    truncate_text,
    extract_domain,
    parse_date_string,
    calculate_text_similarity,
    sanitize_filename,
    extract_keywords,
    normalize_company_name,
    format_currency,
    parse_funding_amount,
    chunk_text,
    merge_dicts,
    safe_get,
)


class TestTruncateText:
    def test_truncate_short(self):
        assert truncate_text("short") == "short"

    def test_truncate_long(self):
        result = truncate_text("a" * 1000, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_truncate_custom_suffix(self):
        result = truncate_text("very long text that exceeds limit", max_length=20, suffix=">>")
        assert result.endswith(">>")


class TestExtractDomain:
    def test_extract_domain_basic(self):
        assert extract_domain("https://example.com/page") == "example.com"

    def test_extract_domain_www(self):
        assert extract_domain("https://www.example.com") == "example.com"

    def test_extract_domain_subdomain(self):
        assert extract_domain("https://api.example.com/v1") == "api.example.com"

    def test_extract_domain_invalid(self):
        assert extract_domain("not-a-url") == "unknown"


class TestParseDateString:
    def test_parse_iso_date(self):
        result = parse_date_string("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_iso_datetime(self):
        result = parse_date_string("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.hour == 10

    def test_parse_human_date(self):
        result = parse_date_string("January 15, 2024")
        assert result is not None
        assert result.month == 1

    def test_parse_invalid(self):
        assert parse_date_string("invalid") is None


class TestCalculateTextSimilarity:
    def test_identical(self):
        assert calculate_text_similarity("hello world", "hello world") == 1.0

    def test_similar(self):
        sim = calculate_text_similarity("hello world", "hello there")
        assert 0.5 < sim < 1.0

    def test_different(self):
        sim = calculate_text_similarity("hello", "goodbye")
        assert sim < 0.5

    def test_case_insensitive(self):
        assert calculate_text_similarity("HELLO", "hello") == 1.0


class TestSanitizeFilename:
    def test_basic(self):
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"

    def test_invalid_chars(self):
        assert sanitize_filename('file<>:"/\\|?*.txt') == "file_________.txt"

    def test_unicode(self):
        result = sanitize_filename("café_naïve.txt")
        assert result == "cafe_naive.txt"

    def test_max_length(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name, max_length=50)
        assert len(result) == 50


class TestExtractKeywords:
    def test_basic(self):
        text = "The quick brown fox jumps over the lazy dog. The fox is quick."
        keywords = extract_keywords(text, max_keywords=5)
        assert "quick" in keywords
        assert "fox" in keywords

    def test_stop_words_filtered(self):
        text = "The and or but in on at to for of with by from as is was are were been be have has had do does did will would could should may might must can"
        keywords = extract_keywords(text)
        assert len(keywords) == 0  # All stop words


class TestNormalizeCompanyName:
    def test_basic(self):
        assert normalize_company_name("Test Corp Inc.") == "test"

    def test_with_tech_suffix(self):
        assert normalize_company_name("TestAI Labs") == "testai"

    def test_remove_punctuation(self):
        assert normalize_company_name("Test-Corp, Inc.") == "test"


class TestFormatCurrency:
    def test_billions(self):
        assert format_currency(1_500_000_000) == "$1.5B"

    def test_millions(self):
        assert format_currency(2_500_000) == "$2.5M"

    def test_thousands(self):
        assert format_currency(50_000) == "$50.0K"

    def test_small(self):
        assert format_currency(500) == "$500"


class TestParseFundingAmount:
    def test_billion(self):
        assert parse_funding_amount("raised $1.5B in series B") == 1_500_000_000

    def test_million(self):
        assert parse_funding_amount("secured $50 million funding") == 50_000_000

    def test_explicit_million(self):
        assert parse_funding_amount("funding of $10 million") == 10_000_000

    def test_none(self):
        assert parse_funding_amount("no numbers here") is None


class TestChunkText:
    def test_short_text(self):
        chunks = chunk_text("short text")
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_long_text(self):
        text = "a" * 5000
        chunks = chunk_text(text, max_chunk_size=1000, overlap=100)
        assert len(chunks) > 1
        # Check overlap
        assert chunks[0][-100:] == chunks[1][:100]


class TestMergeDicts:
    def test_merge(self):
        result = merge_dicts({"a": 1}, {"b": 2}, {"a": 3})
        assert result == {"a": 3, "b": 2}

    def test_empty(self):
        assert merge_dicts() == {}


class TestSafeGet:
    def test_dict_path(self):
        data = {"a": {"b": {"c": 42}}}
        assert safe_get(data, "a.b.c") == 42

    def test_missing_path(self):
        data = {"a": {"b": 1}}
        assert safe_get(data, "a.b.c", default="default") == "default"

    def test_object_attribute(self):
        class Obj:
            def __init__(self):
                self.value = 123

        obj = Obj()
        assert safe_get(obj, "value") == 123
        assert safe_get(obj, "missing", default=0) == 0