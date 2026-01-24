"""
Language auto-detection for syllable extraction.

This module provides automatic language detection functionality using the
langdetect library. It maps ISO 639-1/639-3 language codes to pyphen-compatible
locale codes for seamless integration with the syllable extractor.

The language detection is optional and only used when explicitly requested.
It requires the langdetect package to be installed separately.

Typical Usage:
    >>> from build_tools.pyphen_syllable_extractor import detect_language_code
    >>> text = "Bonjour le monde, comment allez-vous aujourd'hui?"
    >>> code = detect_language_code(text)
    >>> print(code)
    'fr'

    >>> # With custom default
    >>> code = detect_language_code("???", default='en_US')
    >>> print(code)
    'en_US'

    >>> # Check if available
    >>> from build_tools.pyphen_syllable_extractor.language_detection import is_detection_available
    >>> if is_detection_available():
    ...     code = detect_language_code(text)

Note:
    Language detection requires at least 20-50 characters for reliable results.
    Very short text may produce inaccurate detections.
"""

from __future__ import annotations

import warnings

# Optional dependency - only needed if language detection is used
try:
    from langdetect import LangDetectException, detect  # type: ignore[import-not-found]

    LANGDETECT_AVAILABLE = True
except ImportError:
    detect = None  # type: ignore[assignment]
    LangDetectException = Exception  # Fallback for type hints
    LANGDETECT_AVAILABLE = False


# Comprehensive mapping from ISO 639-1/639-3 codes to pyphen locale codes
# Only includes languages supported by pyphen (see languages.py)
# When multiple locales exist (e.g., en_US, en_GB), we choose the most common default
ISO_TO_PYPHEN_MAP: dict[str, str] = {
    # Major European languages
    "en": "en_US",  # English -> US by default (most common)
    "de": "de_DE",  # German -> Germany by default
    "fr": "fr",  # French
    "es": "es",  # Spanish
    "it": "it_IT",  # Italian
    "pt": "pt_PT",  # Portuguese -> Portugal by default
    "nl": "nl_NL",  # Dutch
    "pl": "pl_PL",  # Polish
    "cs": "cs_CZ",  # Czech
    "sk": "sk_SK",  # Slovak
    "ru": "ru_RU",  # Russian
    "uk": "uk_UA",  # Ukrainian
    "bg": "bg_BG",  # Bulgarian
    "hr": "hr_HR",  # Croatian
    "sl": "sl_SI",  # Slovenian
    "ro": "ro_RO",  # Romanian
    "hu": "hu_HU",  # Hungarian
    "el": "el_GR",  # Greek
    "sv": "sv_SE",  # Swedish
    "da": "da_DK",  # Danish
    "no": "nb_NO",  # Norwegian -> Bokmål by default
    "is": "is_IS",  # Icelandic
    "et": "et_EE",  # Estonian
    "lv": "lv_LV",  # Latvian
    "lt": "lt_LT",  # Lithuanian
    # Other European languages
    "ca": "ca",  # Catalan
    "eu": "eu",  # Basque
    "gl": "gl",  # Galician
    "eo": "eo",  # Esperanto
    "be": "be_BY",  # Belarusian
    "sq": "sq_AL",  # Albanian
    "sr": "sr_Cyrl",  # Serbian -> Cyrillic by default
    # Asian languages
    "th": "th_TH",  # Thai
    "id": "id_ID",  # Indonesian
    "mn": "mn_MN",  # Mongolian
    # Indian languages (ISO 639-2/3 codes)
    "as": "as_IN",  # Assamese
    "hi": "hi",  # Hindi -> not in pyphen, will fall back
    "kn": "kn_IN",  # Kannada
    "mr": "mr_IN",  # Marathi
    "or": "or_IN",  # Oriya
    "pa": "pa_IN",  # Punjabi
    "sa": "sa_IN",  # Sanskrit
    "te": "te_IN",  # Telugu
    # African languages
    "af": "af_ZA",  # Afrikaans
    "zu": "zu_ZA",  # Zulu
}

# Alternative locale mappings for specific regions/preferences
# Users can specify these explicitly if they prefer a specific variant
ALTERNATIVE_LOCALES: dict[str, list[str]] = {
    "en": ["en_US", "en_GB"],  # US vs UK English
    "de": ["de_DE", "de_AT", "de_CH"],  # Germany, Austria, Switzerland
    "pt": ["pt_PT", "pt_BR"],  # Portugal vs Brazil
    "no": ["nb_NO", "nn_NO"],  # Bokmål vs Nynorsk
    "sr": ["sr_Cyrl", "sr_Latn"],  # Cyrillic vs Latin Serbian
}


def is_detection_available() -> bool:
    """
    Check if language detection is available.

    Returns:
        True if langdetect is installed and functional, False otherwise.

    Example:
        >>> if is_detection_available():
        ...     print("Language detection is available")
        ... else:
        ...     print("Install langdetect: pip install langdetect")
    """
    return LANGDETECT_AVAILABLE


def detect_language_code(
    text: str,
    default: str = "en_US",
    min_confidence_length: int = 20,
    suppress_warnings: bool = False,
) -> str:
    """
    Auto-detect language from text and return pyphen-compatible language code.

    This function analyzes the input text using langdetect and maps the detected
    ISO 639-1 language code to a pyphen-compatible locale code (e.g., "en" -> "en_US").

    The function requires at least `min_confidence_length` characters for reliable
    detection. Shorter text will return the default language with a warning.

    Args:
        text: Input text to analyze. Should be at least 20-50 characters for
              reliable detection. Mixed-language text may produce unpredictable results.
        default: Default language code to return if detection fails or langdetect
                 is not installed (default: "en_US").
        min_confidence_length: Minimum text length (in characters) required for
                              detection attempt (default: 20). Text shorter than
                              this returns the default language.
        suppress_warnings: If True, suppress warning messages when detection fails
                          or langdetect is unavailable (default: False).

    Returns:
        A pyphen-compatible language code (e.g., "en_US", "de_DE", "fr").
        Returns `default` if detection fails, text is too short, or langdetect
        is not available.

    Raises:
        ImportError: If langdetect is not installed (only when suppress_warnings=False)

    Example:
        >>> # Detect English text
        >>> text = "Hello world, this is a test of language detection"
        >>> detect_language_code(text)
        'en_US'

        >>> # Detect French text
        >>> text = "Bonjour le monde, comment allez-vous aujourd'hui?"
        >>> detect_language_code(text)
        'fr'

        >>> # Short text falls back to default
        >>> detect_language_code("Hello")
        'en_US'

        >>> # Custom default for unknown language
        >>> detect_language_code("???", default='de_DE')
        'de_DE'

        >>> # Suppress warnings for production use
        >>> code = detect_language_code("abc", default='en_US', suppress_warnings=True)

    Note:
        - Detection accuracy decreases significantly with text shorter than 50 chars
        - Mixed-language text detection is unreliable
        - Some languages may map to different locales than expected (e.g., "pt" -> "pt_PT")
        - Use get_alternative_locales() to see all available variants for a language
        - Requires langdetect: pip install langdetect
    """
    # Check if langdetect is available
    if not LANGDETECT_AVAILABLE:
        if not suppress_warnings:
            raise ImportError(
                "langdetect is not installed. Language auto-detection requires langdetect.\n"
                "Install it with: pip install langdetect\n"
                f"Using default language: {default}"
            )
        return default

    # Check minimum text length
    if len(text.strip()) < min_confidence_length:
        if not suppress_warnings:
            warnings.warn(
                f"Text too short for reliable detection ({len(text.strip())} chars). "
                f"Recommended minimum: {min_confidence_length} chars. "
                f"Using default language: {default}"
            )
        return default

    # Attempt language detection
    try:
        iso_code = detect(text)

        # Map ISO code to pyphen locale code
        pyphen_code = ISO_TO_PYPHEN_MAP.get(iso_code)

        if pyphen_code is None:
            if not suppress_warnings:
                warnings.warn(
                    f"Detected language '{iso_code}' is not supported by pyphen. "
                    f"Using default language: {default}"
                )
            return default

        return pyphen_code

    except LangDetectException as e:
        if not suppress_warnings:
            warnings.warn(f"Language detection failed: {e}. Using default language: {default}")
        return default


def get_alternative_locales(iso_code: str) -> list[str] | None:
    """
    Get alternative pyphen locale codes for a given ISO language code.

    Some languages have multiple regional variants (e.g., English has en_US and en_GB).
    This function returns all available pyphen locales for a language.

    Args:
        iso_code: ISO 639-1 language code (e.g., "en", "de", "pt")

    Returns:
        List of pyphen locale codes for the language, or None if not available.
        Returns None if the language has no alternatives (only one locale).

    Example:
        >>> get_alternative_locales("en")
        ['en_US', 'en_GB']

        >>> get_alternative_locales("de")
        ['de_DE', 'de_AT', 'de_CH']

        >>> get_alternative_locales("pt")
        ['pt_PT', 'pt_BR']

        >>> get_alternative_locales("fr")  # Only one variant
        None

        >>> get_alternative_locales("xx")  # Unknown language
        None
    """
    return ALTERNATIVE_LOCALES.get(iso_code)


def get_default_locale(iso_code: str) -> str | None:
    """
    Get the default pyphen locale for an ISO language code.

    This is the locale that will be used by detect_language_code() when
    the specified language is detected.

    Args:
        iso_code: ISO 639-1 language code (e.g., "en", "de", "pt")

    Returns:
        Default pyphen locale code (e.g., "en_US"), or None if language
        is not supported.

    Example:
        >>> get_default_locale("en")
        'en_US'

        >>> get_default_locale("pt")
        'pt_PT'

        >>> get_default_locale("de")
        'de_DE'

        >>> get_default_locale("xx")  # Unknown language
        None
    """
    return ISO_TO_PYPHEN_MAP.get(iso_code)


def list_supported_languages() -> dict[str, str]:
    """
    Get a dictionary of all ISO codes and their default pyphen locales.

    Returns:
        Dictionary mapping ISO 639-1 codes to pyphen locale codes.

    Example:
        >>> langs = list_supported_languages()
        >>> print(f"English: {langs['en']}")
        English: en_US
        >>> print(f"German: {langs['de']}")
        German: de_DE
        >>> print(f"Total languages: {len(langs)}")
        Total languages: 40+
    """
    return ISO_TO_PYPHEN_MAP.copy()
