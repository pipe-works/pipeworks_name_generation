"""
Example: Using the Syllable Extractor

This example demonstrates how to use the syllable_extractor module both
programmatically and as a CLI tool.
"""

from pathlib import Path

from build_tools.pyphen_syllable_extractor import SyllableExtractor

# Example 1: Programmatic usage with filtering
print("=" * 70)
print("Example 1: Programmatic Syllable Extraction (with filtering)")
print("=" * 70)

# Create an extractor for English (US) with length constraints
# min_syllable_length=2, max_syllable_length=6 filters out very short/long fragments
extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=6)

# Extract syllables from sample text
sample_text = """
The ancient forest whispered secrets through rustling leaves.
Mysterious shadows danced beneath the moonlight, creating
an ethereal atmosphere of wonder and enchantment.
"""

# only_hyphenated=True excludes whole words that pyphen couldn't split
syllables = extractor.extract_syllables_from_text(sample_text, only_hyphenated=True)

print(f"\nExtracted {len(syllables)} unique syllables from sample text")
print("Settings: 2-6 characters, only hyphenated words")
print(f"First 20 syllables (sorted): {sorted(syllables)[:20]}")

# Show length distribution
by_length = {}
for syll in syllables:
    by_length.setdefault(len(syll), []).append(syll)

print("\nLength distribution:")
for length in sorted(by_length.keys()):
    print(f"  {length} chars: {len(by_length[length])} syllables")

# Example 2: Process a file
print("\n" + "=" * 70)
print("Example 2: File Processing")
print("=" * 70)

# For this example, we'll use the sample file if it exists
sample_file = Path("_working/sample_input.txt")

if sample_file.exists():
    syllables_from_file = extractor.extract_syllables_from_file(sample_file)
    output_file = Path("_working/extracted_syllables.txt")
    extractor.save_syllables(syllables_from_file, output_file)

    print(f"\n✓ Processed: {sample_file}")
    print(f"✓ Output saved to: {output_file}")
    print(f"✓ Total unique syllables: {len(syllables_from_file)}")
else:
    print(f"\nNote: Sample file not found at {sample_file}")
    print("To use file processing, create a text file and run the CLI tool:")
    print("  python -m pipeworks_name_generation.syllable_extractor")

# Example 3: Different languages
print("\n" + "=" * 70)
print("Example 3: Multi-language Support")
print("=" * 70)

languages = [
    ("en_US", "Hello world"),
    ("es", "Hola mundo"),
    ("de_DE", "Hallo Welt"),
    ("fr", "Bonjour le monde"),
]

for lang_code, text in languages:
    try:
        lang_extractor = SyllableExtractor(lang_code)
        lang_syllables = lang_extractor.extract_syllables_from_text(text)
        print(f"\n{lang_code:8s} | '{text}' → {sorted(lang_syllables)}")
    except ValueError as e:
        print(f"\n{lang_code:8s} | Not available: {e}")

print("\n" + "=" * 70)
print("CLI Usage")
print("=" * 70)
print("\nTo use the interactive CLI tool:")
print("  python -m build_tools.pyphen_syllable_extractor")
print("\nThe CLI will guide you through:")
print("  1. Selecting a language from 50+ supported options")
print("  2. Providing an input text file")
print("  3. Specifying an output file for the extracted syllables")
print("=" * 70)
