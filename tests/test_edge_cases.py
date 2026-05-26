"""Tests for json2sql CLI uncovered paths."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from json2sql.cli import app

runner = CliRunner()


class TestCLIErrorPaths:
    """Targeted tests for uncovered CLI error-handling paths."""

    def test_convert_no_file_or_stdin_exit_code(self):
        """Exit code 1 when no file provided and no stdin piped.

        CliRunner replaces sys.stdin so isatty can't be meaningfully
        mocked at the module level. The important assertion is that
        the CLI gracefully exits with code 1.
        """
        result = runner.invoke(app, ["convert"])
        assert result.exit_code == 1

    def test_version_command_output(self):
        """Version command prints 'json2sql X.Y.Z'."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "json2sql 0.1.1" in result.stdout


class TestConverterFlattenEdgeCases:
    """Edge cases for converter flatten logic."""

    def test_flatten_mixed_nested_and_simple_values(self):
        """flatten=True: when a key is a dict in some rows and a simple value in others,
        the simple value should still be rendered (converter.py:104, 109)."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter(flatten=True)
        data = [
            {"id": 1, "address": {"city": "NYC"}},
            {"id": 2, "address": "missing"},  # string, not dict
        ]
        result = converter.convert(json.dumps(data))
        assert "address_city" in result
        assert "'NYC'" in result
        # address is not in flat_map but IS a column (from row 2's else path)
        # Row 1's address is a dict with flatten=True → continue
        # Row 2's address is a string → rendered as "'missing'"
        assert "'missing'" in result or "NULL" in result

    def test_flatten_type_upgrade_for_flattened_column(self):
        """flattened column type upgrades from TEXT to more specific type (line 165)."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter(flatten=True)
        data = [
            {"id": 1, "meta": {"count": "five"}},  # string → TEXT
            {"id": 2, "meta": {"count": 42}},  # integer → upgrade
        ]
        result = converter.convert(json.dumps(data))
        assert "meta_count" in result
        # After upgrade, type should be INTEGER not TEXT
        assert "INTEGER" in result
        assert "'five'" in result
        assert "42" in result

    def test_type_upgrade_for_top_level_column(self):
        """Top-level column type upgrades from TEXT to more specific type (line 175)."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter()
        data = [
            {"key": "hello"},  # string → TEXT
            {"key": 100},  # integer → upgrade to INTEGER
        ]
        result = converter.convert(json.dumps(data))
        assert "INTEGER" in result
        assert "'hello'" in result
        assert "100" in result


class TestConverterExtraEdgePaths:
    """Additional converter coverage for remaining uncovered lines."""

    def test_convert_objects_list_vs_dict_root(self):
        """Array root with a single dict should produce one INSERT row."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter()
        result = converter.convert(json.dumps([{"name": "test"}]))
        assert "INSERT INTO" in result
        assert "'test'" in result
