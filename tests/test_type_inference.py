"""Tests for robust column type inference across mixed values.

Regression coverage for the bug where a column holding mixed value types
(e.g. a string and an integer) was inferred as the non-text type, producing
SQL that inserts a quoted string literal into a numeric column -- which is
rejected by databases such as PostgreSQL.
"""

import json

from json2sql.converter import JSONToSQLConverter
from json2sql.dialects import Dialect


class TestMixedTypeInference:
    def test_string_then_int_falls_back_to_text(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        data = json.dumps([{"val": "string"}, {"val": 42}])
        result = conv.convert(data, table_name="mixed")
        assert '"val" TEXT' in result, "mixed string/int column must be TEXT"
        assert "'string'" in result

    def test_int_then_string_falls_back_to_text(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        data = json.dumps([{"val": 42}, {"val": "string"}])
        result = conv.convert(data, table_name="mixed")
        assert '"val" TEXT' in result

    def test_int_float_column_widens_to_float(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        data = json.dumps([{"n": 1}, {"n": 2.5}])
        result = conv.convert(data, table_name="nums")
        assert '"n" DOUBLE PRECISION' in result

    def test_bool_int_mixed_falls_back_to_text(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        data = json.dumps([{"flag": True}, {"flag": 1}])
        result = conv.convert(data, table_name="flags")
        assert '"flag" TEXT' in result

    def test_uniform_types_unaffected(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        data = json.dumps([{"age": 30}, {"age": 25}])
        result = conv.convert(data, table_name="users")
        assert '"age" INTEGER' in result

    def test_trailing_null_does_not_widen(self):
        conv = JSONToSQLConverter(dialect=Dialect.POSTGRES)
        data = json.dumps([{"age": 30}, {"age": None}])
        result = conv.convert(data, table_name="users")
        assert '"age" INTEGER' in result
