"""
Language configuration for pyphen hyphenation.

This module provides language mappings and utilities for pyphen's LibreOffice
hyphenation dictionaries.
"""

from __future__ import annotations

# Mapping of language names to pyphen locale codes
# Based on pyphen's LibreOffice dictionary support
SUPPORTED_LANGUAGES: dict[str, str] = {
    "Afrikaans": "af_ZA",
    "Albanian": "sq_AL",
    "Assamese": "as_IN",
    "Basque": "eu",
    "Belarusian": "be_BY",
    "Bulgarian": "bg_BG",
    "Catalan": "ca",
    "Croatian": "hr_HR",
    "Czech": "cs_CZ",
    "Danish": "da_DK",
    "Dutch": "nl_NL",
    "English (UK)": "en_GB",
    "English (US)": "en_US",
    "Esperanto": "eo",
    "Estonian": "et_EE",
    "French": "fr",
    "Galician": "gl",
    "German": "de_DE",
    "German (Austria)": "de_AT",
    "German (Switzerland)": "de_CH",
    "Greek": "el_GR",
    "Hungarian": "hu_HU",
    "Icelandic": "is_IS",
    "Indonesian": "id_ID",
    "Italian": "it_IT",
    "Kannada": "kn_IN",
    "Lithuanian": "lt_LT",
    "Latvian": "lv_LV",
    "Marathi": "mr_IN",
    "Mongolian": "mn_MN",
    "Norwegian (Bokmål)": "nb_NO",
    "Norwegian (Nynorsk)": "nn_NO",
    "Oriya": "or_IN",
    "Polish": "pl_PL",
    "Portuguese (Brazil)": "pt_BR",
    "Portuguese (Portugal)": "pt_PT",
    "Punjabi": "pa_IN",
    "Romanian": "ro_RO",
    "Russian": "ru_RU",
    "Sanskrit": "sa_IN",
    "Serbian (Cyrillic)": "sr_Cyrl",
    "Serbian (Latin)": "sr_Latn",
    "Slovak": "sk_SK",
    "Slovenian": "sl_SI",
    "Spanish": "es",
    "Swedish": "sv_SE",
    "Telugu": "te_IN",
    "Thai": "th_TH",
    "Ukrainian": "uk_UA",
    "Zulu": "zu_ZA",
}


def get_language_code(language_name: str) -> str | None:
    """
    Get pyphen language code from language name.

    Args:
        language_name: Full language name (e.g., "English (US)")

    Returns:
        Language code (e.g., "en_US") or None if not found

    Example:
        >>> get_language_code("English (US)")
        'en_US'
    """
    return SUPPORTED_LANGUAGES.get(language_name)


def get_language_name(code: str) -> str | None:
    """
    Get language name from pyphen code.

    Args:
        code: Pyphen language code (e.g., "en_US")

    Returns:
        Language name (e.g., "English (US)") or None if not found

    Example:
        >>> get_language_name("en_US")
        'English (US)'
    """
    for name, lang_code in SUPPORTED_LANGUAGES.items():
        if lang_code == code:
            return name
    return None


def validate_language_code(code: str) -> bool:
    """
    Check if a language code is supported.

    Args:
        code: Pyphen language code to validate

    Returns:
        True if the code is supported, False otherwise

    Example:
        >>> validate_language_code("en_US")
        True
        >>> validate_language_code("invalid")
        False
    """
    return code in SUPPORTED_LANGUAGES.values()
