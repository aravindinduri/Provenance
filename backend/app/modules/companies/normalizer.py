"""
app/modules/companies/normalizer.py — Entity normalization rules (Stage 0).

Architecture reference: §G.1 Stage 0 & Stage 2.
Implements:
  - Unicode NFKD/NFKC diacritics stripping
  - Legal corporate suffix removal (global & regional)
  - Punctuation stripping & whitespace collapse
  - Free-mail domain rejection for domain matching (Stage 2)
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

# Free-mail domains to reject from domain matching (Stage 2)
FREE_MAIL_DOMAINS: frozenset[str] = frozenset({
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "yahoo.co.in",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "msn.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "aol.com",
    "zoho.com",
    "proton.me",
    "protonmail.com",
    "mail.com",
    "gmx.com",
    "yandex.com",
    "yandex.ru",
    "qq.com",
    "163.com",
    "126.com",
    "sina.com",
    "rediffmail.com",
})

# Common corporate legal suffixes to strip (ordered from multi-word to single-word)
LEGAL_SUFFIXES: list[str] = [
    # Multi-word suffixes
    r"\bprivate\s+limited\b",
    r"\bpvt\s+ltd\b",
    r"\bpvt\s+limited\b",
    r"\bco\s+ltd\b",
    r"\bco\s+limited\b",
    r"\bcorp\s+ltd\b",
    r"\bpty\s+ltd\b",
    r"\bsp\s+z\s+o\s+o\b",
    r"\bs\s+r\s+o\b",
    r"\bs\s+p\s+a\b",
    r"\bs\s+a\s+r\s+l\b",
    r"\bs\s+a\s+s\b",
    r"\ba\s+s\b",
    r"\bs\s+a\b",
    # Single-word / acronym suffixes
    r"\bcorporation\b",
    r"\bholdings?\b",
    r"\bincorporated\b",
    r"\blimited\b",
    r"\bcompany\b",
    r"\binc\b",
    r"\bcorp\b",
    r"\bltd\b",
    r"\bllc\b",
    r"\bllp\b",
    r"\bgmbh\b",
    r"\bag\b",
    r"\bplc\b",
    r"\bbv\b",
    r"\bnv\b",
    r"\bsa\b",
    r"\bpvt\b",
    r"\bco\b",
    r"\boy\b",
    r"\bab\b",
    r"\bsarl\b",
    r"\bpt\b",
    r"\btbk\b",
    r"\bkg\b",
    r"\bkgaa\b",
    r"\bspa\b",
    r"\bsro\b",
    r"\bcie\b",
    r"\bcie\s+kg\b",
]

# Compile suffix pattern to strip from end of string or right after name
_SUFFIX_REGEX = re.compile(
    r"(?:,\s*|\s+)(" + "|".join(LEGAL_SUFFIXES) + r")(?:\.|\b|\s)*$",
    re.IGNORECASE,
)


def strip_accents(text: str) -> str:
    """Normalize unicode and strip combining accent marks/diacritics."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_company_name(name: str, strip_suffixes: bool = False) -> str:
    """
    Normalizes company name for matching and trigram search.
    By default (strip_suffixes=False), strips diacritics/accents, lowercases,
    removes punctuation, and collapses whitespace (matching Phase 4 behavior).
    When strip_suffixes=True (Stage 0 ER), also strips corporate legal suffixes.
    """
    if not name or not name.strip():
        return ""

    # Diacritics & lowercase
    s = strip_accents(name).lower().strip()

    if strip_suffixes:
        # Strip periods inside words (e.g., "pvt. ltd." -> "pvt ltd", "u.s." -> "us")
        s = s.replace(".", " ")
        # Iteratively strip legal suffixes (e.g. "Acme Holdings LLC" -> "Acme Holdings" -> "Acme")
        for _ in range(3):
            cleaned = _SUFFIX_REGEX.sub("", s).strip()
            if cleaned == s:
                break
            s = cleaned

    # Replace all non-alphanumeric characters with spaces
    s = re.sub(r"[^\w\s]", " ", s)

    # Collapse multiple whitespaces
    s = " ".join(s.split())
    return s


def normalize_for_resolution(name: str) -> str:
    """
    Stage 0 Normalization for Entity Resolution:
    Lowercase, strip accents, strip legal suffixes, collapse whitespace.
    """
    return normalize_company_name(name, strip_suffixes=True)



def normalize_domain(domain_or_url: str | None) -> str | None:
    """
    Normalize domain string or URL:
      - Strips protocol, port, paths, query strings, and email prefixes
      - Strips leading www.
      - Returns lowercase hostname
      - Returns None if empty or invalid
    """
    if not domain_or_url:
        return None

    raw = domain_or_url.strip().lower()
    if not raw:
        return None

    if "@" in raw:
        raw = raw.split("@")[-1].strip()

    # If full URL, parse hostname
    if "://" in raw:
        parsed = urlparse(raw)
        host = parsed.hostname or ""
    else:
        # Just domain string or domain/path
        host = raw.split("/")[0].split(":")[0]

    # Strip leading www.
    if host.startswith("www."):
        host = host[4:]

    host = host.strip()
    return host if host else None


def is_free_mail_domain(domain: str | None) -> bool:
    """Check if domain is a known public/free-mail service."""
    if not domain:
        return False
    norm = normalize_domain(domain)
    return norm in FREE_MAIL_DOMAINS if norm else False
