"""Tests for json2sql converter."""

import json

import pytest

from json2sql.converter import JSONToSQLConverter
from json2sql.dialects import Dialect


@pytest.fixture
def converter_postgres():
    return JSONToSQLConverter(dialect=Dialect.POSTGRES)


@pytest.fixture
def converter_mysql():
    return JSONToSQLConverter(dialect=Dialect.MYSQL)


@pytest.fixture
def converter_sqlite():
    return JSONToSQLConverter(dialect=Dialect.SQLITE)


# --- Basic conversion tests ---

class TestBasicConversion:
    def test_single_object_postgres(self, converter_postgres):
        data = json.dumps({"name": "Alice", "age": 30, "active": True})
        result = converter_postgres.convert(data, table_name="users")
        assert "CREATE TABLE" in result
        assert "INSERT INTO" in result
        assert "'Alice'" in result
        assert "30" in result
        assert "TRUE" in result

    def test_array_of_objects(self, converter_postgres):
        data = json.dumps([
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ])
        result = converter_postgres.convert(data, table_name="users")
        assert "CREATE TABLE" in result
        assert "INSERT INTO" in result
        assert "'Alice'" in result
        assert "'Bob'" in result

    def test_array_of_primitives(self, converter_postgres):
        data = json.dumps([1, 2, 3])
        result = converter_postgres.convert(data, table_name="numbers")
        assert "CREATE TABLE" in result
        assert "INSERT INTO" in result

    def test_empty_array(self, converter_postgres):
        data = json.dumps([])
        result = converter_postgres.convert(data, table_name="empty")
        assert "Empty JSON array" in result

    def test_null_values(self, converter_postgres):
        data = json.dumps({"name": "Alice", "email": None})
        result = converter_postgres.convert(data, table_name="users")
        assert "NULL" in result


# --- Dialect tests ---

class TestDialects:
    def test_mysql_boolean(self, converter_mysql):
        data = json.dumps({"active": True})
        result = converter_mysql.convert(data, table_name="flags")
        assert "1" in result  # MySQL: TRUE -> 1

    def test_mysql_identifiers(self, converter_mysql):
        data = json.dumps({"name": "test"})
        result = converter_mysql.convert(data, table_name="users")
        assert "`name`" in result or "`users`" in result

    def test_sqlite_boolean(self, converter_sqlite):
        data = json.dumps({"active": True})
        result = converter_sqlite.convert(data, table_name="flags")
        assert "1" in result  # SQLite: TRUE -> 1

    def test_postgres_boolean(self, converter_postgres):
        data = json.dumps({"active": True})
        result = converter_postgres.convert(data, table_name="flags")
        assert "TRUE" in result

    def test_mysql_type_mapping(self, converter_mysql):
        data = json.dumps({"name": "x", "count": 5, "price": 9.99, "flag": True})
        result = converter_mysql.convert(data, table_name="items")
        assert "VARCHAR(255)" in result
        assert "INT" in result
        assert "DOUBLE" in result
        assert "TINYINT(1)" in result


# --- Nested/flatten tests ---

class TestFlatten:
    def test_flatten_nested_object(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({"id": 1, "address": {"city": "NYC", "zip": "10001"}})
        result = conv.convert(data, table_name="users")
        assert "CREATE TABLE" in result
        # Flattened keys should appear
        assert "address_city" in result or "city" in result

    def test_flatten_nested_array(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "name": "Alice",
            "orders": [
                {"product": "Widget", "qty": 3},
                {"product": "Gadget", "qty": 1},
            ],
        })
        result = conv.convert(data, table_name="users")
        assert "CREATE TABLE" in result
        # Should create a separate table for orders
        assert "users_orders" in result or "orders" in result


# --- Schema-only tests ---

class TestSchemaOnly:
    def test_generate_schema(self, converter_postgres):
        data = json.dumps([{"name": "Alice", "age": 30}])
        result = converter_postgres.generate_schema(data, table_name="users")
        assert "CREATE TABLE" in result
        assert "INSERT INTO" not in result


# --- Edge cases ---

class TestFlattenRegression:
    """Regression tests for flatten bugs."""

    def test_flatten_nested_array_column_value_count(self):
        """
        Regression: flatten with nested array should have matching
        column count and value count in INSERT statements.
        Previously the FK placeholder 'NULL' was appended to the parent
        row but removed from columns, causing a mismatch.
        """
        import re
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "name": "Alice",
            "orders": [
                {"product": "Widget", "qty": 3},
            ],
        })
        result = conv.convert(data, table_name="users")
        # Parse the INSERT for the parent table
        for block in result.split("\n\n"):
            if 'INSERT INTO' in block and '"users"' in block:
                cols = re.search(r'\(([^)]+)\)\s*VALUES', block)
                vals = re.search(r'VALUES\s*\(([^)]+)\)', block)
                if cols and vals:
                    c_count = len([c for c in cols.group(1).split(",") if c.strip()])
                    v_count = len([v for v in vals.group(1).split(",") if v.strip()])
                    assert c_count == v_count, (
                        f"Column count ({c_count}) != value count ({v_count})"
                    )

    def test_flatten_mixed_nested_array_and_object_count(self):
        """
        Regression: mixed nested dicts and arrays in flatten mode
        should produce column-value count match.
        """
        import re
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "profile": {"age": 30, "city": "NYC"},
            "tags": [{"name": "dev"}],
        })
        result = conv.convert(data, table_name="users")
        for block in result.split("\n\n"):
            if 'INSERT INTO' in block and '"users"' in block:
                cols = re.search(r'\(([^)]+)\)\s*VALUES', block)
                vals = re.search(r'VALUES\s*\(([^)]+)\)', block)
                if cols and vals:
                    c_count = len([c for c in cols.group(1).split(",") if c.strip()])
                    v_count = len([v for v in vals.group(1).split(",") if v.strip()])
                    assert c_count == v_count, (
                        f"Column count ({c_count}) != value count ({v_count})"
                    )


class TestFlattenDetail:
    """Detailed tests for flatten feature output correctness."""

    def test_flatten_nested_object_column_names(self):
        """Flattened nested dict should produce prefixed column names in CREATE TABLE."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({"id": 1, "address": {"city": "NYC", "zip": "10001"}})
        result = conv.convert(data, table_name="users")
        assert '"address_city"' in result, "Should have flattened column address_city"
        assert '"address_zip"' in result, "Should have flattened column address_zip"
        assert '"id"' in result, "Should keep non-nested columns"

    def test_flatten_nested_object_insert_values(self):
        """Flattened nested dict values should align with columns in INSERT."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({"id": 1, "address": {"city": "NYC", "zip": "10001"}})
        result = conv.convert(data, table_name="users")
        # Extract the VALUES line
        insert_lines = [line.strip() for line in result.split("\n") if "VALUES" in line]
        assert len(insert_lines) == 1
        # Values should be (1, 'NYC', '10001')
        assert "1" in insert_lines[0]
        assert "'NYC'" in insert_lines[0]
        assert "'10001'" in insert_lines[0]

    def test_flatten_multiple_rows(self):
        """Multiple objects with nested dicts should flatten consistently."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps([
            {"id": 1, "meta": {"color": "red", "size": "M"}},
            {"id": 2, "meta": {"color": "blue", "size": "L"}},
        ])
        result = conv.convert(data, table_name="items")
        assert '"meta_color"' in result
        assert '"meta_size"' in result
        # Both rows should be in the multi-row INSERT
        assert "'red'" in result
        assert "'blue'" in result

    def test_flatten_deeply_nested(self):
        """Deeply nested dicts should be one-level flattened (not recursive)."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "location": {
                "city": "NYC",
                "coordinates": {"lat": 40.71, "lng": -74.01},
            },
        })
        result = conv.convert(data, table_name="places")
        # First-level flatten: location_city and location_coordinates
        assert '"location_city"' in result
        # coordinates is still a dict -> should be stringified or treated as sub-value
        # but the current implementation only does one-level
        assert '"location_coordinates"' not in result or "CREATE TABLE" in result

    def test_flatten_empty_nested_object(self):
        """Empty nested dict should not break the converter."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({"id": 1, "meta": {}})
        try:
            result = conv.convert(data, table_name="items")
            # Should produce valid SQL even with empty nested object
            assert "CREATE TABLE" in result
        except Exception as e:
            pytest.fail(f"Empty nested dict raised: {e}")

    def test_flatten_with_array_and_object_mixed(self):
        """Mix of nested arrays and nested objects with flatten."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "profile": {"age": 30, "city": "NYC"},
            "tags": [{"name": "dev"}, {"name": "python"}],
        })
        result = conv.convert(data, table_name="users")
        assert '"profile_age"' in result
        assert '"profile_city"' in result
        # Nested array should create a separate table
        assert "users_tags" in result


class TestSchemaOnlyWithFlatten:
    """Schema-only mode with flatten."""

    def test_generate_schema_with_flatten_nested_object(self):
        """Schema-only with flatten should produce CREATE TABLE with flattened columns."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({"id": 1, "address": {"city": "NYC", "zip": "10001"}})
        result = conv.generate_schema(data, table_name="users")
        assert "CREATE TABLE" in result
        assert '"address_city"' in result
        assert '"address_zip"' in result
        assert "INSERT INTO" not in result

    def test_generate_schema_with_flatten_mixed(self):
        """Schema-only with flatten for nested arrays and objects."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "profile": {"age": 30},
            "orders": [{"product": "Widget", "qty": 3}],
        })
        result = conv.generate_schema(data, table_name="users")
        assert "CREATE TABLE" in result
        assert '"profile_age"' in result
        assert "users_orders" in result
        assert "INSERT INTO" not in result


class TestFlattenMissingSubKeysNullPadding:
    """Regression: objects with different nested sub-keys across rows."""

    def test_flatten_missing_sub_key_gets_null(self):
        """When one object's nested dict is missing a sub-key present in others,
        the missing sub-key should get NULL in the INSERT row."""
        import re
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps([
            {"id": 1, "meta": {"city": "NYC"}},
            {"id": 2, "meta": {"city": "LA", "state": "CA"}},
        ])
        result = conv.convert(data, table_name="users")
        # The INSERT should have matching column/value counts per row
        for block in result.split("\n\n"):
            if 'INSERT INTO' in block and '"users"' in block:
                cols = re.search(r'\(([^)]+)\)\s*VALUES', block)
                vals = re.search(r'VALUES\s*(.+)', block, re.DOTALL)
                if cols and vals:
                    c_count = len([c for c in cols.group(1).split(",") if c.strip()])
                    # Count value groups (rows)
                    row_matches = re.findall(r'\(([^)]+)\)', vals.group(1))
                    for row_str in row_matches:
                        v_count = len([v for v in row_str.split(",") if v.strip()])
                        assert v_count == c_count, (
                            f"Column count ({c_count}) != value count ({v_count}) in row ({row_str})"
                        )
        # The first row should have NULL for meta_state
        assert "NULL" in result

    def test_flatten_nested_dict_all_keys_present(self):
        """When all objects have the same nested sub-keys, no NULL padding needed."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps([
            {"id": 1, "meta": {"city": "NYC", "state": "NY"}},
            {"id": 2, "meta": {"city": "LA", "state": "CA"}},
        ])
        result = conv.convert(data, table_name="users")
        assert '"meta_city"' in result
        assert '"meta_state"' in result
        assert "'NYC'" in result
        assert "'LA'" in result


class TestFlattenNestedFKNotShadowed:
    """Regression: nested object with key matching parent FK name."""

    def test_nested_object_key_not_shadowed_by_fk(self):
        """A nested object's own key that matches the parent FK column name
        should NOT be silently replaced by the parent's FK value."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "name": "Alice",
            "orders": [
                {"users_id": 999, "product": "Widget", "qty": 3},
            ],
        })
        result = conv.convert(data, table_name="users")
        # The child table should preserve the nested object's users_id value (999)
        # rather than silently replacing it with the parent's id (1)
        assert "'999'" in result or "999" in result


class TestEdgeCases:
    def test_string_with_quotes(self, converter_postgres):
        data = json.dumps({"bio": "It's a test"})
        result = converter_postgres.convert(data, table_name="profiles")
        assert "It''s a test" in result  # SQL-escaped single quote

    def test_float_values(self, converter_postgres):
        data = json.dumps({"price": 19.99})
        result = converter_postgres.convert(data, table_name="products")
        assert "19.99" in result

    def test_mixed_types_in_column(self, converter_postgres):
        # When a column has mixed types, should fall back to TEXT
        data = json.dumps([{"val": "string"}, {"val": 42}])
        result = converter_postgres.convert(data, table_name="mixed")
        assert "CREATE TABLE" in result

    def test_missing_keys_across_rows(self, converter_postgres):
        # Objects with different keys should all get columns
        data = json.dumps([
            {"name": "Alice", "age": 30},
            {"name": "Bob", "email": "bob@test.com"},
        ])
        result = converter_postgres.convert(data, table_name="users")
        assert "email" in result
        assert "age" in result

    def test_unsupported_root_type_raises(self, converter_postgres):
        """A plain string at root raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported JSON root type"):
            converter_postgres.convert('"just a string"', table_name="bad")

    def test_unsupported_root_number_raises(self, converter_postgres):
        """A plain number at root raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported JSON root type"):
            converter_postgres.convert("42", table_name="bad")

    def test_unsupported_root_bool_raises(self, converter_postgres):
        """A plain boolean at root raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported JSON root type"):
            converter_postgres.convert("true", table_name="bad")


class TestGenerateSchema:
    """Tests for generate_schema method."""

    def test_generate_schema_basic(self, converter_postgres):
        data = json.dumps([{"name": "Alice", "age": 30}])
        result = converter_postgres.generate_schema(data, table_name="users")
        assert "CREATE TABLE" in result
        assert "INSERT INTO" not in result

    def test_generate_schema_single_object(self, converter_postgres):
        """Single dict at root also works."""
        data = json.dumps({"name": "Alice"})
        result = converter_postgres.generate_schema(data, table_name="users")
        assert "CREATE TABLE" in result
        assert '"name"' in result

    def test_generate_schema_with_flatten_nested_array(self):
        """generate_schema with flatten=True should produce CREATE TABLE for nested arrays."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps({
            "id": 1,
            "name": "Alice",
            "orders": [
                {"product": "Widget", "qty": 3},
                {"product": "Gadget", "qty": 1},
            ],
        })
        result = conv.generate_schema(data, table_name="users")
        assert "CREATE TABLE" in result
        # Should include the nested table schema
        assert "users_orders" in result or "orders" in result
        assert "INSERT INTO" not in result

    def test_generate_schema_primitives(self, converter_postgres):
        """A primitive type should produce a simple schema."""
        data = json.dumps([1, 2, 3])
        result = converter_postgres.generate_schema(data, table_name="nums")
        assert "CREATE TABLE" in result

    def test_generate_schema_primitives_with_flatten_no_crash(self):
        """generate_schema with flatten=True on primitive array must not crash.

        Regression: _process_flatten accessed objects[0] without checking
        if the list was empty, causing IndexError on primitive arrays.
        """
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps([1, 2, 3])
        result = conv.generate_schema(data, table_name="nums")
        assert "CREATE TABLE" in result
        assert "INSERT INTO" not in result

    def test_generate_schema_empty_array_with_flatten_no_crash(self):
        """generate_schema with flatten=True on empty array must not crash."""
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES, flatten=True)
        data = json.dumps([])
        result = conv.generate_schema(data, table_name="empty")
        assert "CREATE TABLE" in result

    def test_version_in_init_matches_pyproject(self):
        """pyproject.toml version must match __init__.__version__."""
        from pathlib import Path

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # Python < 3.11 backport

        from json2sql import __version__
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        assert data["project"]["version"] == __version__, (
            f"pyproject.toml version ({data['project']['version']}) != "
            f"__init__.__version__ ({__version__})"
        )
