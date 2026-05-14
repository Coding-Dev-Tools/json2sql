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
