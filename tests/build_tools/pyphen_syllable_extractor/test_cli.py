"""
Tests for pyphen_syllable_extractor CLI.

Tests for module imports and shared CLI utilities integration.
"""


class TestCliImports:
    """Test that CLI module imports correctly."""

    def test_cli_module_imports(self):
        """Test that CLI module can be imported."""
        from build_tools.pyphen_syllable_extractor import cli

        # Verify module attributes exist
        assert hasattr(cli, "CORPUS_DB_AVAILABLE")
        assert hasattr(cli, "READLINE_AVAILABLE")
        assert hasattr(cli, "discover_files")
        assert hasattr(cli, "input_with_completion")
        assert hasattr(cli, "record_corpus_db_safe")

    def test_cli_uses_shared_utilities(self):
        """Test that CLI uses shared utilities from tui_common."""
        from build_tools.pyphen_syllable_extractor import cli
        from build_tools.tui_common import cli_utils

        # Verify CLI uses the shared functions
        assert cli.CORPUS_DB_AVAILABLE == cli_utils.CORPUS_DB_AVAILABLE
        assert cli.READLINE_AVAILABLE == cli_utils.READLINE_AVAILABLE
        assert cli.discover_files is cli_utils.discover_files
        assert cli.input_with_completion is cli_utils.input_with_completion
        assert cli.record_corpus_db_safe is cli_utils.record_corpus_db_safe

    def test_corpus_ledger_import_when_available(self):
        """Test that CorpusLedger is imported when available."""
        from build_tools.pyphen_syllable_extractor import cli

        if cli.CORPUS_DB_AVAILABLE:
            # CorpusLedger should be importable from the cli module
            assert hasattr(cli, "CorpusLedger")


class TestArgumentParser:
    """Test argument parser creation."""

    def test_create_argument_parser_exists(self):
        """Test that create_argument_parser function exists."""
        from build_tools.pyphen_syllable_extractor.cli import create_argument_parser

        parser = create_argument_parser()
        assert parser is not None

    def test_parser_has_required_arguments(self):
        """Test that parser has expected arguments."""
        from build_tools.pyphen_syllable_extractor.cli import create_argument_parser

        parser = create_argument_parser()
        # Check some known arguments exist
        # Get all option strings from the parser
        option_strings: list[str] = []
        for action in parser._actions:
            option_strings.extend(action.option_strings)

        # Verify key arguments are present
        assert "--source" in option_strings or "-s" in option_strings
        assert "--output" in option_strings or "-o" in option_strings
