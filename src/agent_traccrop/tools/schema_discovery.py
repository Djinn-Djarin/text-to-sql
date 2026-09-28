from typing import Any, Dict, List, Optional

from langchain_community.utilities import SQLDatabase


class SQLDiscoveryTool:
    def __init__(
        self,
        connection_string: str,
        schema_name: Optional[str] = None,
        include_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
    ):
        self.connection_string = self._normalize_connection_string(connection_string)
        self.schema_name = schema_name
        self.include_tables = include_tables
        self.sample_rows_in_table_info = sample_rows_in_table_info
        self._schema_cache: Optional[Dict[str, Any]] = None
        self._create_db()

    @staticmethod
    def _normalize_connection_string(connection_string: str) -> str:
        """Use the psycopg 3 SQLAlchemy driver for PostgreSQL URLs."""
        if connection_string.startswith("postgres://"):
            return "postgresql+psycopg://" + connection_string[len("postgres://") :]
        if connection_string.startswith("postgresql://"):
            return "postgresql+psycopg://" + connection_string[len("postgresql://") :]
        return connection_string

    def _create_db(self) -> None:
        self.db = SQLDatabase.from_uri(
            database_uri=self.connection_string,
            schema=self.schema_name,
            include_tables=self.include_tables,
            sample_rows_in_table_info=self.sample_rows_in_table_info,
        )

    def discover_schema(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Discover table structures, columns, and data types, and cache the result.
        """
        if self._schema_cache is not None and not force_refresh:
            return self._schema_cache

        if force_refresh:
            self._create_db()

        table_names = list(self.db.get_usable_table_names())
        formatted_schema = self.db.get_table_info(table_names)

        self._schema_cache = {
            "dialect": self.db.dialect,
            "usable_tables": table_names,
            "formatted_schema": formatted_schema,
        }

        return self._schema_cache

    def get_formatted_schema(self, force_refresh: bool = False) -> str:
        """Return the LLM-ready schema string."""
        schema_data = self.discover_schema(force_refresh=force_refresh)
        return schema_data["formatted_schema"]


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    connecting_string = os.getenv("DATABASE_URL_DEV")
    if not connecting_string:
        raise SystemExit("DATABASE_URL_DEV is not configured")

    result = SQLDiscoveryTool(connecting_string, schema_name="public")
    print(result.get_formatted_schema())
