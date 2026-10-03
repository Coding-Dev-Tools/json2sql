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
        """Flattened column mixing a string and int collapses to TEXT (line 165)."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter(flatten=True)
        data = [
            {"id": 1, "meta": {"count": "five"}},  # string -> TEXT
            {"id": 2, "meta": {"count": 42}},  # integer -> mixed -> TEXT
        ]
        result = converter.convert(json.dumps(data))
        assert "meta_count" in result
        # The flattened meta_count column saw a string AND an integer, so it must
        # be TEXT (not widened to INTEGER) to keep the generated SQL valid.
        assert "TEXT" in result
        assert "'five'" in result
        assert "42" in result

    def test_type_upgrade_for_top_level_column(self):
        """Mixed-type column collapses to TEXT so the generated SQL is valid.

        A column that mixes a string and an integer must become TEXT (not
        INTEGER): otherwise the string literal would be inserted into a numeric
        column and rejected by Postgres/MySQL. See ``converter._merge_type``.
        """
        from json2sql.converter import JSONToSQLConverter

        data = [
            {"key": "hello"},  # string -> TEXT
            {"key": 100},  # integer -> would be INTEGER, but mixed -> TEXT
        ]
        # Non-flatten path (_infer_columns)
        result = JSONToSQLConverter().convert(json.dumps(data))
        assert "TEXT" in result
        assert "INTEGER" not in result  # must NOT widen to a numeric type
        assert "'hello'" in result
        assert "100" in result

        # Flatten path (_infer_columns_flattened else branch)
        result2 = JSONToSQLConverter(flatten=True).convert(json.dumps(data))
        assert "TEXT" in result2
        assert "INTEGER" not in result2
        assert "'hello'" in result2
        assert "100" in result2


class TestConverterExtraEdgePaths:
    """Additional converter coverage for remaining uncovered lines."""

    def test_convert_objects_list_vs_dict_root(self):
        """Array root with a single dict should produce one INSERT row."""
        from json2sql.converter import JSONToSQLConverter

        converter = JSONToSQLConverter()
        result = converter.convert(json.dumps([{"name": "test"}]))
        assert "INSERT INTO" in result
        assert "'test'" in result


def test_flatten_multiple_parent_rows_single_child_table():
    """Multiple parent rows with nested arrays yield ONE child table with all rows."""
    import json as _json

    from json2sql.converter import JSONToSQLConverter

    data = [
        {"id": 1, "name": "a", "tags": [{"label": "x", "score": 1}]},
        {
            "id": 2,
            "name": "b",
            "tags": [{"label": "y", "score": 2}, {"label": "z", "score": 3}],
        },
    ]
    text = _json.dumps(data)
    out = JSONToSQLConverter(flatten=True).convert(text, "users")
    assert out.count('CREATE TABLE "users_tags"') == 1
    assert "'z', 3" in out and "'y', 2" in out and "'x', 1" in out

    schema = JSONToSQLConverter(flatten=True).generate_schema(text, "users")
    assert schema.count('CREATE TABLE "users_tags"') == 1


def test_flatten_child_rows_keep_own_parent_fk():
    """Each child row links to its own parent via the FK column."""
    import json as _json

    from json2sql.converter import JSONToSQLConverter

    data = [
        {"id": 10, "items": [{"sku": "a1"}]},
        {"id": 20, "items": [{"sku": "b1"}]},
    ]
    out = JSONToSQLConverter(flatten=True).convert(_json.dumps(data), "orders")
    assert "(10, 'a1')" in out
    assert "(20, 'b1')" in out
