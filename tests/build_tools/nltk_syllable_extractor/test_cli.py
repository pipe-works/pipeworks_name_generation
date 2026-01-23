"""
Tests for nltk_syllable_extractor CLI.

Tests for module imports and shared CLI utilities integration.
"""

from unittest.mock import patch

import pytest


class TestCliImports:
    """Test that CLI module imports correctly."""

    def test_cli_module_imports(self):
        """Test that CLI module can be imported."""
        from build_tools.nltk_syllable_extractor import cli

        # Verify module attributes exist
        assert hasattr(cli, "CORPUS_DB_AVAILABLE")
        assert hasattr(cli, "READLINE_AVAILABLE")
        assert hasattr(cli, "discover_files")
        assert hasattr(cli, "input_with_completion")
        assert hasattr(cli, "record_corpus_db_safe")

    def test_cli_uses_shared_utilities(self):
        """Test that CLI uses shared utilities from tui_common."""
        from build_tools.nltk_syllable_extractor import cli
        from build_tools.tui_common import cli_utils

        # Verify CLI uses the shared functions
        assert cli.CORPUS_DB_AVAILABLE == cli_utils.CORPUS_DB_AVAILABLE
        assert cli.READLINE_AVAILABLE == cli_utils.READLINE_AVAILABLE
        assert cli.discover_files is cli_utils.discover_files
        assert cli.input_with_completion is cli_utils.input_with_completion
        assert cli.record_corpus_db_safe is cli_utils.record_corpus_db_safe

    def test_corpus_ledger_import_when_available(self):
        """Test that CorpusLedger is imported when available."""
        from build_tools.nltk_syllable_extractor import cli

        if cli.CORPUS_DB_AVAILABLE:
            # CorpusLedger should be importable from the cli module
            assert hasattr(cli, "CorpusLedger")


class TestArgumentParser:
    """Test argument parser creation."""

    def test_create_argument_parser_exists(self):
        """Test that create_argument_parser function exists."""
        from build_tools.nltk_syllable_extractor.cli import create_argument_parser

        parser = create_argument_parser()
        assert parser is not None

    def test_parser_has_required_arguments(self):
        """Test that parser has expected arguments."""
        from build_tools.nltk_syllable_extractor.cli import create_argument_parser

        parser = create_argument_parser()
        # Check some known arguments exist
        # Get all option strings from the parser
        option_strings: list[str] = []
        for action in parser._actions:
            option_strings.extend(action.option_strings)

        # Verify key arguments are present
        assert "--source" in option_strings or "-s" in option_strings
        assert "--output" in option_strings or "-o" in option_strings


class TestMainFunction:
    """Test main() function mode selection."""

    def test_main_calls_batch_mode_with_file_arg(self):
        """Test main() calls run_batch when --file is provided."""
        with patch("sys.argv", ["prog", "--file", "test.txt"]):
            # Patch at the batch module level since import happens inside main()
            with patch("build_tools.nltk_syllable_extractor.batch.run_batch") as mock_batch:
                from build_tools.nltk_syllable_extractor.cli import main

                # Avoid calling real batch mode
                mock_batch.side_effect = SystemExit(0)

                try:
                    main()
                except SystemExit:
                    pass

                mock_batch.assert_called_once()

    def test_main_calls_batch_mode_with_files_arg(self):
        """Test main() calls run_batch when --files is provided."""
        with patch("sys.argv", ["prog", "--files", "test1.txt", "test2.txt"]):
            with patch("build_tools.nltk_syllable_extractor.batch.run_batch") as mock_batch:
                from build_tools.nltk_syllable_extractor.cli import main

                mock_batch.side_effect = SystemExit(0)

                try:
                    main()
                except SystemExit:
                    pass

                mock_batch.assert_called_once()

    def test_main_calls_batch_mode_with_source_arg(self):
        """Test main() calls run_batch when --source is provided."""
        with patch("sys.argv", ["prog", "--source", "/path/to/dir"]):
            with patch("build_tools.nltk_syllable_extractor.batch.run_batch") as mock_batch:
                from build_tools.nltk_syllable_extractor.cli import main

                mock_batch.side_effect = SystemExit(0)

                try:
                    main()
                except SystemExit:
                    pass

                mock_batch.assert_called_once()

    def test_main_calls_interactive_mode_with_no_args(self):
        """Test main() calls run_interactive when no batch args provided."""
        with patch("sys.argv", ["prog"]):
            # Patch at the interactive module level since import happens inside main()
            with patch(
                "build_tools.nltk_syllable_extractor.interactive.run_interactive"
            ) as mock_interactive:
                from build_tools.nltk_syllable_extractor.cli import main

                # Make interactive mode return immediately
                mock_interactive.return_value = None

                main()

                mock_interactive.assert_called_once()

    def test_main_returns_zero_on_success(self):
        """Test main() returns 0 on successful execution."""
        from build_tools.nltk_syllable_extractor.cli import main

        with patch(
            "build_tools.nltk_syllable_extractor.interactive.run_interactive"
        ) as mock_interactive:
            mock_interactive.return_value = None
            result = main([])

        assert result == 0

    def test_main_returns_130_on_keyboard_interrupt(self):
        """Test main() returns 130 on KeyboardInterrupt."""
        from build_tools.nltk_syllable_extractor.cli import main

        with patch(
            "build_tools.nltk_syllable_extractor.interactive.run_interactive",
            side_effect=KeyboardInterrupt(),
        ):
            result = main([])

        assert result == 130

    def test_main_returns_1_on_exception(self, capsys: pytest.CaptureFixture[str]):
        """Test main() returns 1 on general exception."""
        from build_tools.nltk_syllable_extractor.cli import main

        with patch(
            "build_tools.nltk_syllable_extractor.interactive.run_interactive",
            side_effect=RuntimeError("Test error"),
        ):
            result = main([])

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Test error" in captured.err
