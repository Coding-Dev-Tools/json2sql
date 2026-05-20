"""Core JSON-to-SQL conversion logic."""

import json

from .dialects import (
    Dialect,
    create_table_sql,
    format_value,
    insert_sql,
    sql_type_for,
)


class JSONToSQLConverter:
    """Convert JSON data to SQL INSERT statements."""

    def __init__(self, dialect: Dialect = Dialect.POSTGRES, flatten: bool = False):
        self.dialect = dialect
        self.flatten = flatten
        self._extra_tables: list[tuple[str, dict[str, str], list[list[str]]]] = []

    def convert(self, json_text: str, table_name: str = "data") -> str:
        """Convert JSON text to SQL statements."""
        data = json.loads(json_text)
        statements: list[str] = []
        self._extra_tables = []

        if isinstance(data, list):
            # Array of objects -> multiple rows
            if not data:
                return "-- Empty JSON array, no SQL generated."
            if isinstance(data[0], dict):
                statements.append(self._convert_objects(data, table_name))
            else:
                # Array of primitives -> single column
                statements.append(self._convert_primitives(data, table_name))
        elif isinstance(data, dict):
            # Single object -> one row
            statements.append(self._convert_objects([data], table_name))
        else:
            raise ValueError(f"Unsupported JSON root type: {type(data).__name__}")

        # Add any extra tables from flattening
        for name, columns, rows in self._extra_tables:
            statements.insert(0, create_table_sql(name, columns, self.dialect))
            statements.append(insert_sql(name, list(columns.keys()), rows, self.dialect))

        return "\n\n".join(statements)

    def generate_schema(self, json_text: str, table_name: str = "data") -> str:
        """Generate only CREATE TABLE statements from JSON data."""
        data = json.loads(json_text)
        self._extra_tables = []

        if isinstance(data, list) and data and isinstance(data[0], dict):
            objects = data
        elif isinstance(data, dict):
            objects = [data]
        else:
            objects = []

        if objects:
            if self.flatten:
                columns = self._infer_columns_flattened(objects, table_name)
            else:
                columns = self._infer_columns(objects)
        else:
            columns = {"value": "TEXT"}

        statements = [create_table_sql(table_name, columns, self.dialect)]

        # Process extra tables from flattening
        self._process_flatten(objects, table_name)
        for name, cols, _ in self._extra_tables:
            statements.append(create_table_sql(name, cols, self.dialect))

        return "\n\n".join(statements)

    def _convert_objects(self, objects: list[dict], table_name: str) -> str:
        """Convert a list of JSON objects to SQL."""
        columns = self._infer_columns(objects)
        rows: list[list[str]] = []

        for obj in objects:
            row: list[str] = []
            for col_name in columns:
                value = obj.get(col_name)
                if self.flatten and isinstance(value, list) and value and isinstance(value[0], dict):
                    # Nested array of objects -> separate table
                    self._flatten_nested(table_name, col_name, value, obj)
                    row.append("NULL")  # FK placeholder
                elif self.flatten and isinstance(value, dict):
                    # Nested object -> flatten into parent with prefixed keys
                    self._flatten_object(table_name, col_name, value, obj, row)
                    continue  # skip the original column
                else:
                    row.append(format_value(value, self.dialect))
            rows.append(row)

        # Re-infer columns if flattening added new ones
        if self.flatten:
            columns = self._infer_columns_flattened(objects, table_name)

        parts = [create_table_sql(table_name, columns, self.dialect)]
        if rows:
            parts.append(insert_sql(table_name, list(columns.keys()), rows, self.dialect))
        return "\n\n".join(parts)

    def _convert_primitives(self, values: list, table_name: str) -> str:
        """Convert a list of primitive values to SQL."""
        col_type = sql_type_for(values[0] if values else None, self.dialect)
        columns = {"value": col_type}
        rows = [[format_value(v, self.dialect)] for v in values]
        parts = [create_table_sql(table_name, columns, self.dialect)]
        parts.append(insert_sql(table_name, ["value"], rows, self.dialect))
        return "\n\n".join(parts)

    def _infer_columns(self, objects: list[dict]) -> dict[str, str]:
        """Infer column names and types from a list of objects."""
        columns: dict[str, str] = {}
        for obj in objects:
            for key, value in obj.items():
                if key not in columns:
                    columns[key] = sql_type_for(value, self.dialect)
                elif value is not None:
                    # Upgrade type if we find a non-null value
                    inferred = sql_type_for(value, self.dialect)
                    if columns[key] == "TEXT" and inferred != "TEXT":
                        columns[key] = inferred
        return columns

    def _infer_columns_flattened(self, objects: list[dict], table_name: str) -> dict[str, str]:
        """Infer columns after flattening nested objects."""
        columns: dict[str, str] = {}
        for obj in objects:
            for key, value in obj.items():
                if isinstance(value, dict) and self.flatten:
                    for sub_key, sub_value in value.items():
                        flat_key = f"{key}_{sub_key}"
                        if flat_key not in columns:
                            columns[flat_key] = sql_type_for(sub_value, self.dialect)
                elif isinstance(value, list) and value and isinstance(value[0], dict) and self.flatten:
                    # Skip - goes to separate table
                    pass
                else:
                    if key not in columns:
                        columns[key] = sql_type_for(value, self.dialect)
        return columns

    def _flatten_nested(
        self,
        parent_table: str,
        key: str,
        nested_objects: list[dict],
        parent_obj: dict,
    ) -> None:
        """Flatten a nested array of objects into a separate table."""
        child_table = f"{parent_table}_{key}"
        columns = self._infer_columns(nested_objects)
        # Add parent reference
        # Use first unique field from parent as FK
        parent_ref = None
        for pk in ("id", "name", parent_table + "_id"):
            if pk in parent_obj:
                parent_ref = pk
                break
        if parent_ref:
            columns = {f"{parent_table}_{parent_ref}": sql_type_for(parent_obj[parent_ref], self.dialect), **columns}

        rows: list[list[str]] = []
        for nested in nested_objects:
            row: list[str] = []
            if parent_ref:
                row.append(format_value(parent_obj.get(parent_ref), self.dialect))
            for col_name in columns:
                if col_name == f"{parent_table}_{parent_ref}":
                    continue
                row.append(format_value(nested.get(col_name), self.dialect))
            rows.append(row)

        self._extra_tables.append((child_table, columns, rows))

    def _flatten_object(
        self,
        parent_table: str,
        key: str,
        nested: dict,
        parent_obj: dict,
        row: list[str],
    ) -> None:
        """Flatten a nested object into parent row with prefixed keys."""
        for _sub_key, sub_value in nested.items():
            row.append(format_value(sub_value, self.dialect))

    def _process_flatten(self, objects: list, table_name: str) -> None:
        """Process flattening for schema generation."""
        if not self.flatten:
            return
        for obj in objects if isinstance(objects[0], dict) else []:
            for key, value in obj.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    self._flatten_nested(table_name, key, value, obj)
