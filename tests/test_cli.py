"""Tests for the json2sql CLI interface."""

import json
from json2sql.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestCLIBasic:
    """Basic CLI command tests."""

    def test_convert_json_file(self, tmp_path):
        """Convert a simple JSON file to SQL via CLI."""
        data = {"name": "Alice", "age": 30}
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps(data))

        result = runner.invoke(app, ["convert", str(json_file)])
        assert result.exit_code == 0
        assert "CREATE TABLE" in result.stdout
        assert "INSERT INTO" in result.stdout
        assert "'Alice'" in result.stdout
        assert "30" in result.stdout

    def test_convert_with_table_name(self, tmp_path):
        """Specify custom table name."""
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"x": 1}))

        result = runner.invoke(app, ["convert", str(json_file), "--table", "my_table"])
        assert result.exit_code == 0
        assert "CREATE TABLE" in result.stdout
        assert "my_table" in result.stdout

    def test_convert_with_dialect_mysql(self, tmp_path):
        """Use MySQL dialect via CLI."""
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"active": True}))

        result = runner.invoke(app, ["convert", str(json_file), "--dialect", "mysql"])
        assert result.exit_code == 0
        assert "`active` TINYINT(1)" in result.stdout or "`active`" in result.stdout

    def test_convert_with_dialect_sqlite(self, tmp_path):
        """Use SQLite dialect via CLI."""
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"price": 9.99}))

        result = runner.invoke(app, ["convert", str(json_file), "--dialect", "sqlite"])
        assert result.exit_code == 0
        assert "REAL" in result.stdout

    def test_convert_output_file(self, tmp_path):
        """Write SQL to an output file."""
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"name": "test"}))
        out_file = tmp_path / "out.sql"

        result = runner.invoke(app, ["convert", str(json_file), "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "CREATE TABLE" in content
        assert "INSERT INTO" in content

    def test_convert_with_flatten(self, tmp_path):
        """Flatten nested JSON via CLI."""
        data = {"id": 1, "address": {"city": "NYC"}}
        json_file = tmp_path / "nested.json"
        json_file.write_text(json.dumps(data))

        result = runner.invoke(app, ["convert", str(json_file), "--flatten"])
        assert result.exit_code == 0
        assert "CREATE TABLE" in result.stdout

    def test_convert_schema_only(self, tmp_path):
        """Generate schema-only output (no INSERT)."""
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps([{"name": "Alice", "age": 30}]))

        result = runner.invoke(app, ["convert", str(json_file), "--schema-only"])
        assert result.exit_code == 0
        assert "CREATE TABLE" in result.stdout
        assert "INSERT INTO" not in result.stdout

    def test_convert_stdin(self):
        """Read JSON from stdin."""
        result = runner.invoke(app, ["convert"], input=json.dumps({"name": "stdin_test"}))
        assert result.exit_code == 0
        assert "'stdin_test'" in result.stdout

    def test_convert_empty_stdin_no_input(self):
        """Error when no file and stdin is empty."""
        # Simulate no input (isatty = True in CliRunner)
        result = runner.invoke(app, ["convert"])
        assert result.exit_code == 1
        assert "Error" in result.stderr or "Error" in result.stdout

    def test_convert_bad_json(self, tmp_path):
        """Error on invalid JSON input."""
        json_file = tmp_path / "bad.json"
        json_file.write_text("{invalid}")

        result = runner.invoke(app, ["convert", str(json_file)])
        assert result.exit_code == 1
        assert "Error" in result.stderr or "Error" in result.stdout

    def test_convert_bad_dialect(self, tmp_path):
        """Error on invalid dialect."""
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"x": 1}))

        result = runner.invoke(app, ["convert", str(json_file), "--dialect", "oracle"])
        assert result.exit_code != 0

    def test_convert_file_not_found(self):
        """Error when file does not exist."""
        result = runner.invoke(app, ["convert", "nonexistent.json"])
        # Typer validates exists=True so it should fail
        assert result.exit_code != 0


class TestCLIVersion:
    """Version command tests."""

    def test_version(self):
        """Show version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestCLIErrorHandling:
    """Error handling tests."""

    def test_no_args_shows_help(self):
        """Running without args shows help."""
        result = runner.invoke(app)
        # Typer with no_args_is_help may exit 0 or 2 depending on version
        assert "Usage:" in result.stdout or "Usage:" in result.stderr or "Convert" in result.stdout or "Convert" in result.stderr

    def test_convert_array_of_objects(self, tmp_path):
        """Convert array of objects via CLI."""
        data = [{"name": "Alice"}, {"name": "Bob"}]
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps(data))

        result = runner.invoke(app, ["convert", str(json_file)])
        assert result.exit_code == 0
        assert "'Alice'" in result.stdout
        assert "'Bob'" in result.stdout

    def test_convert_empty_array(self, tmp_path):
        """Empty array produces appropriate message."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("[]")

        result = runner.invoke(app, ["convert", str(json_file)])
        assert result.exit_code == 0
        assert "Empty" in result.stdout

    def test_convert_boolean_values(self, tmp_path):
        """Boolean rendering depends on dialect."""
        data = {"flag": True, "active": False}
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps(data))

        # Postgres
        result = runner.invoke(app, ["convert", str(json_file), "--dialect", "postgres"])
        assert result.exit_code == 0
        assert "TRUE" in result.stdout
        assert "FALSE" in result.stdout

    def test_convert_null_values(self, tmp_path):
        """NULL values handled."""
        data = {"name": None}
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps(data))

        result = runner.invoke(app, ["convert", str(json_file)])
        assert result.exit_code == 0
        assert "NULL" in result.stdout
