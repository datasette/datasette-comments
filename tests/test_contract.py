import pytest
from pydantic import ValidationError
from datasette_comments.contract import (
    ApiThreadNewParams,
    ApiThreadNewParamsDatabase,
    ApiThreadNewParamsTable,
    ApiThreadNewParamsRow,
    ApiThreadNewParamsColumn,
    ApiThreadNewParamsValue,
)


class TestApiThreadNewParams:
    """Test the discriminated union for thread creation parameters"""

    def test_database_type_valid(self):
        """Test valid database type thread creation"""
        data = {
            "type": "database",
            "database": "mydb",
            "comment": "This is a comment on the database",
        }
        # Pydantic v2 uses model_validate
        result = ApiThreadNewParamsDatabase.model_validate(data)
        assert result.type == "database"
        assert result.database == "mydb"
        assert result.comment == "This is a comment on the database"

    def test_database_type_missing_database(self):
        """Test database type fails without database field"""
        data = {
            "type": "database",
            "comment": "This is a comment",
        }
        with pytest.raises(ValidationError) as exc_info:
            ApiThreadNewParamsDatabase.model_validate(data)
        assert "database" in str(exc_info.value)

    def test_table_type_valid(self):
        """Test valid table type thread creation"""
        data = {
            "type": "table",
            "database": "mydb",
            "table": "users",
            "comment": "Comment on the users table",
        }
        result = ApiThreadNewParamsTable.model_validate(data)
        assert result.type == "table"
        assert result.database == "mydb"
        assert result.table == "users"
        assert result.comment == "Comment on the users table"

    def test_table_type_missing_table(self):
        """Test table type fails without table field"""
        data = {
            "type": "table",
            "database": "mydb",
            "comment": "Comment",
        }
        with pytest.raises(ValidationError) as exc_info:
            ApiThreadNewParamsTable.model_validate(data)
        assert "table" in str(exc_info.value)

    def test_row_type_valid(self):
        """Test valid row type thread creation"""
        data = {
            "type": "row",
            "database": "mydb",
            "table": "users",
            "rowids": "1",
            "comment": "Comment on row 1",
        }
        result = ApiThreadNewParamsRow.model_validate(data)
        assert result.type == "row"
        assert result.database == "mydb"
        assert result.table == "users"
        assert result.rowids == "1"
        assert result.comment == "Comment on row 1"

    def test_row_type_multiple_rowids(self):
        """Test row type with tilde-encoded compound primary key"""
        data = {
            "type": "row",
            "database": "mydb",
            "table": "users",
            "rowids": "1,abc~2Fdef",
            "comment": "Comment on compound key row",
        }
        result = ApiThreadNewParamsRow.model_validate(data)
        assert result.rowids == "1,abc~2Fdef"

    def test_row_type_missing_rowids(self):
        """Test row type fails without rowids field"""
        data = {
            "type": "row",
            "database": "mydb",
            "table": "users",
            "comment": "Comment",
        }
        with pytest.raises(ValidationError) as exc_info:
            ApiThreadNewParamsRow.model_validate(data)
        assert "rowids" in str(exc_info.value)

    def test_column_type_valid(self):
        """Test valid column type thread creation"""
        data = {
            "type": "column",
            "database": "mydb",
            "table": "users",
            "column": "email",
            "comment": "Comment on email column",
        }
        result = ApiThreadNewParamsColumn.model_validate(data)
        assert result.type == "column"
        assert result.database == "mydb"
        assert result.table == "users"
        assert result.column == "email"
        assert result.comment == "Comment on email column"

    def test_column_type_missing_column(self):
        """Test column type fails without column field"""
        data = {
            "type": "column",
            "database": "mydb",
            "table": "users",
            "comment": "Comment",
        }
        with pytest.raises(ValidationError) as exc_info:
            ApiThreadNewParamsColumn.model_validate(data)
        assert "column" in str(exc_info.value)

    def test_value_type_valid(self):
        """Test valid value type thread creation"""
        data = {
            "type": "value",
            "database": "mydb",
            "table": "users",
            "column": "email",
            "rowids": "123",
            "comment": "Comment on specific value",
        }
        result = ApiThreadNewParamsValue.model_validate(data)
        assert result.type == "value"
        assert result.database == "mydb"
        assert result.table == "users"
        assert result.column == "email"
        assert result.rowids == "123"
        assert result.comment == "Comment on specific value"

    def test_value_type_missing_column(self):
        """Test value type fails without column field"""
        data = {
            "type": "value",
            "database": "mydb",
            "table": "users",
            "rowids": "123",
            "comment": "Comment",
        }
        with pytest.raises(ValidationError) as exc_info:
            ApiThreadNewParamsValue.model_validate(data)
        assert "column" in str(exc_info.value)

    def test_value_type_missing_rowids(self):
        """Test value type fails without rowids field"""
        data = {
            "type": "value",
            "database": "mydb",
            "table": "users",
            "column": "email",
            "comment": "Comment",
        }
        with pytest.raises(ValidationError) as exc_info:
            ApiThreadNewParamsValue.model_validate(data)
        assert "rowids" in str(exc_info.value)

    def test_missing_comment_fails(self):
        """Test that all types require a comment field"""
        data = {
            "type": "database",
            "database": "mydb",
        }
        with pytest.raises(ValidationError) as exc_info:
            ApiThreadNewParamsDatabase.model_validate(data)
        assert "comment" in str(exc_info.value)

    def test_invalid_type(self):
        """Test that invalid type value fails validation"""
        data = {
            "type": "invalid_type",
            "database": "mydb",
            "comment": "Comment",
        }
        with pytest.raises(ValidationError):
            ApiThreadNewParamsDatabase.model_validate(data)
        # Should fail because "invalid_type" is not a valid literal for database type


class TestApiThreadNewParamsDiscrimination:
    """Test that the discriminated union works correctly via JSON parsing"""

    def test_discriminator_selects_database(self):
        """Test discriminator picks DatabaseParams for type='database'"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ApiThreadNewParams)
        data = {
            "type": "database",
            "database": "mydb",
            "comment": "Database comment",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, ApiThreadNewParamsDatabase)
        assert result.database == "mydb"

    def test_discriminator_selects_table(self):
        """Test discriminator picks TableParams for type='table'"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ApiThreadNewParams)
        data = {
            "type": "table",
            "database": "mydb",
            "table": "users",
            "comment": "Table comment",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, ApiThreadNewParamsTable)
        assert result.table == "users"

    def test_discriminator_selects_row(self):
        """Test discriminator picks RowParams for type='row'"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ApiThreadNewParams)
        data = {
            "type": "row",
            "database": "mydb",
            "table": "users",
            "rowids": "1",
            "comment": "Row comment",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, ApiThreadNewParamsRow)
        assert result.rowids == "1"

    def test_discriminator_selects_column(self):
        """Test discriminator picks ColumnParams for type='column'"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ApiThreadNewParams)
        data = {
            "type": "column",
            "database": "mydb",
            "table": "users",
            "column": "email",
            "comment": "Column comment",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, ApiThreadNewParamsColumn)
        assert result.column == "email"

    def test_discriminator_selects_value(self):
        """Test discriminator picks ValueParams for type='value'"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ApiThreadNewParams)
        data = {
            "type": "value",
            "database": "mydb",
            "table": "users",
            "column": "email",
            "rowids": "1",
            "comment": "Value comment",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, ApiThreadNewParamsValue)
        assert result.column == "email"
        assert result.rowids == "1"

    def test_discriminator_fails_missing_required_field(self):
        """Test that discriminator validation catches missing required fields"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ApiThreadNewParams)
        # Row type missing rowids
        data = {
            "type": "row",
            "database": "mydb",
            "table": "users",
            "comment": "Row comment",
        }
        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_python(data)
        assert "rowids" in str(exc_info.value)

    def test_discriminator_fails_invalid_type(self):
        """Test that invalid type value fails discrimination"""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ApiThreadNewParams)
        data = {
            "type": "nonexistent",
            "database": "mydb",
            "comment": "Comment",
        }
        with pytest.raises(ValidationError):
            adapter.validate_python(data)
        # Should fail to match any union member
