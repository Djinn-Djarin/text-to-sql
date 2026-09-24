import sqlglot
from sqlglot import exp
from src.agent_traccrop.db import pool
from langchain_core.tools import tool
from typing import Set, Tuple, Optional
from langchain_core.runnables import RunnableConfig

class SQLQueryValidator:
    def __init__(
        self,
        allowed_tables: Optional[Set[str]] = None,
        denied_tables: Optional[Set[str]] = None,
        dialect: str = "postgres"
    ):
        self.allowed_tables = {t.lower() for t in allowed_tables} if allowed_tables is not None else None
        self.denied_tables = {t.lower() for t in denied_tables} if denied_tables is not None else set()
        self.dialect = dialect

    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        try:
            expressions = sqlglot.parse(sql, read=self.dialect)
        except Exception as e:
            return False, f"SQL Syntax Error: {e}"

        if len(expressions) != 1:
            return False, "Only single-statement queries are permitted."

        ast = expressions[0]
        if ast is None:
            return False, "Empty query."

        # Read-only validation
        if not isinstance(ast, (exp.Select, exp.Union)):
            return False, f"Forbidden statement type. Only SELECT queries are permitted."

        if ast.find(exp.Into):
            return False, "Query contains 'INTO' clause (table creation/mutation is not permitted)."

        mutating_statements = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.AlterTable)
        if ast.find(mutating_statements):
            return False, "Data-modifying operations are not allowed in CTEs or subqueries."

        # Extract tables
        cte_aliases = set()
        with_clause = ast.args.get("with")
        if with_clause:
            for cte in with_clause.expressions:
                cte_aliases.add(cte.alias_or_name.lower())

        referenced_tables = set()
        for table in ast.find_all(exp.Table):
            table_name = table.name.lower()
            if table_name and table_name not in cte_aliases:
                referenced_tables.add(table_name)

        # Check blacklists and whitelists
        blocked = referenced_tables.intersection(self.denied_tables)
        if blocked:
            return False, f"Access denied to blacklisted table(s): {', '.join(blocked)}"

        if self.allowed_tables is not None:
            unauthorized = referenced_tables - self.allowed_tables
            if unauthorized:
                return False, f"Access denied to unauthorized table(s): {', '.join(unauthorized)}"

        return True, None


# Initialize the validator with your specific table rules
validator = SQLQueryValidator(
    allowed_tables={"harvests", "crops", "fields"},  # Add tables the AI IS allowed to query
    denied_tables={"users", "passwords", "roles"},   # Add tables the AI is NEVER allowed to query
    dialect="postgres"
)

def execute_secure_sql(query: str, user_id: str) -> str:
    """
    Executes an AI-generated SQL query securely by validating it is read-only
    and then enforcing Row-Level Security.
    """
    # 1. Validate the query before ever touching the database
    is_valid, error_msg = validator.validate(query)
    if not is_valid:
        # Return the validation error to the AI so it knows why it failed
        return f"Query rejected by security policy: {error_msg}"

    # 2. If valid, proceed with the secure RLS transaction
    try:
        with pool.connection() as conn:
            with conn.transaction():
                # Set the RLS session variable for this specific transaction
                conn.execute(
                    "SELECT set_config('app.current_user_id', %s, true);", 
                    (user_id,)
                )
                
                # Execute the validated, read-only AI query
                cursor = conn.execute(query)
                
                if cursor.description:
                    results = cursor.fetchall()
                    return str(results) 
                else:
                    return "Query executed successfully (no data returned)."
                    
    except Exception as e:
        return f"Database error: {str(e)}"

@tool
def query_database(query:str, config:RunnableConfig) -> str:
    """Use this tool to query the CropTrac database for user data. 
    Input must be a valid PostgreSQL query."""

    user_id = config['configurable']['thread_id']

    # Call your secure execution function
    return execute_secure_sql(query, user_id)

# Export the tools list so the graph can use it
tools = [query_database]