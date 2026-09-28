import json
import sqlglot
from sqlglot import exp
from src.agent_traccrop.db import pool, DATABASE_URL
from langchain_core.tools import tool
from typing import Set, Tuple, Optional
from langchain_core.runnables import RunnableConfig
from src.agent_traccrop.tools.schema_discovery import SQLDiscoveryTool
from src.agent_traccrop.tools.table_metadata import get_table_description

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

        mutating_statements = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter)
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
                if table.db and table.db.lower() != 'ai_views':
                    return False, f"Security Violation: You must use the 'ai_views' schema (e.g., ai_views.{table_name}) instead of {table.db}."
                if not table.db:
                    return False, f"Security Violation: You must explicitly use the 'ai_views' schema (e.g., ai_views.{table_name})."
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


TABLE_SECURITY_CONFIG = {
    # Direct account_id tables
    "_01_user_management_accountmember": {"type": "direct"},
    "_02_site_site": {"type": "direct"},
    "_03_crop_customcrop": {"type": "direct"},
    "_04_equipment_equipment": {"type": "direct"},
    "_07_spraycard_spraycard": {"type": "direct"},

    # Global tables (no filtering)
    "_03_crop_globalcrop": {"type": "global"},
    "_03_crop_globalvariety": {"type": "global"},
    "_04_equipment_equipmenttype": {"type": "global"},
    "_06_chemical_chemical": {"type": "global"},
    "_06_chemical_chemicalcropdata": {"type": "global"},

    # Tables requiring JOIN traversal to account_id
    "_01_user_management_userprofile": {"type": "join", "target": "_01_user_management_accountmember", "source_col": "uid", "target_col": "user_id"},
    "_01_user_management_employeeprofile": {"type": "join", "target": "_01_user_management_accountmember", "source_col": "user_id", "target_col": "user_id"},
    "_02_site_sitecrop": {"type": "join", "target": "_02_site_site", "source_col": "site_id", "target_col": "sid"},
    "_02_site_sitecropvariety": {"type": "join", "target": "_02_site_sitecrop", "source_col": "site_crop_id", "target_col": "scid"},
    "_03_crop_customvariety": {"type": "direct"}, # Has account_id natively
    "_07_spraycard_spraycardcropselection": {"type": "join", "target": "_07_spraycard_spraycard", "source_col": "spray_card_id", "target_col": "spray_card_id"},
    "_07_spraycard_spraycardsitetreatment": {"type": "join", "target": "_07_spraycard_spraycard", "source_col": "spray_card_id", "target_col": "spray_card_id"},
    "_07_spraycard_spraycardchemical": {"type": "join", "target": "_07_spraycard_spraycard", "source_col": "spray_card_id", "target_col": "spray_card_id"},
    "_07_spraycard_spraycardequipment": {"type": "join", "target": "_07_spraycard_spraycard", "source_col": "spray_card_id", "target_col": "spray_card_id"},
    "_07_spraycard_cropgrowthstage": {"type": "join", "target": "_01_user_management_accountmember", "source_col": "user_id", "target_col": "user_id"},
}

def sync_ai_views():
    """Dynamically generates and executes CREATE VIEW statements based on TABLE_SECURITY_CONFIG."""
    sql_statements = ["CREATE SCHEMA IF NOT EXISTS ai_views;"]
    
    for table, config in TABLE_SECURITY_CONFIG.items():
        if config["type"] == "direct":
            sql = f"""CREATE OR REPLACE VIEW ai_views.{table} AS 
                      SELECT * FROM public.{table} 
                      WHERE account_id = current_setting('app.account_id', true);"""
        elif config["type"] == "global":
            sql = f"""CREATE OR REPLACE VIEW ai_views.{table} AS 
                      SELECT * FROM public.{table};"""
        elif config["type"] == "join":
            target = config["target"]
            scol = config["source_col"]
            tcol = config["target_col"]
            sql = f"""CREATE OR REPLACE VIEW ai_views.{table} AS 
                      SELECT t.* FROM public.{table} t 
                      WHERE t.{scol} IN (SELECT {tcol} FROM ai_views.{target});"""
        sql_statements.append(sql)
        
    try:
        with pool.connection() as conn:
            for stmt in sql_statements:
                conn.execute(stmt)
            print("Successfully synced AI Secure Views.")
    except Exception as e:
        print(f"Failed to sync AI Views: {e}")

# Run the sync once on module import to ensure views are ready
sync_ai_views()

# Initialize the validator with your specific table rules
validator = SQLQueryValidator(
    allowed_tables=set(TABLE_SECURITY_CONFIG.keys()),
    denied_tables={"users", "passwords", "roles"},   # Add tables the AI is NEVER allowed to query
    dialect="postgres"
)

def execute_secure_sql(query: str, user_id: str, account_id: str) -> str:
    """
    Executes an AI-generated SQL query securely by validating it is read-only
    and then enforcing Row-Level Security.
    """
    is_valid, error_msg = validator.validate(query)
    if not is_valid:
        return f"Query rejected by security policy: {error_msg}"

    try:
        with pool.connection() as conn:
            with conn.transaction():
                conn.execute("SELECT set_config('app.current_user_id', %s, true);", (user_id,))
                conn.execute("SELECT set_config('app.account_id', %s, true);", (account_id,))
                
                cursor = conn.execute(query)
                if cursor.description:
                    return str(cursor.fetchall()) 
                return "Query executed successfully (no data returned)."
    except Exception as e:
        return f"Database error: {str(e)}"

@tool
def query_database(query:str, config:RunnableConfig) -> str:
    """Use this tool to query the CropTrac database for user data. 
    Input must be a valid PostgreSQL query."""
    user_id = config['configurable']['user_id']
    account_id = config['configurable']['account_id']
    return execute_secure_sql(query, user_id, account_id)


def get_table_hierarchy_info(table_name: str) -> str:
    """Extract Parent (outgoing FKs) and Child (incoming FKs) relationships for a table."""
    parents = []
    children = []
    try:
        with pool.connection() as conn:
            # Outgoing FKs (Parents)
            p_cursor = conn.execute('''
                SELECT kcu.column_name, ccu.table_name, ccu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='public' AND tc.table_name = %s;
            ''', (table_name,))
            for row in p_cursor.fetchall():
                parents.append(f"  - {row[1]} (via {row[0]} -> {row[2]})")

            # Incoming FKs (Children)
            c_cursor = conn.execute('''
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='public' AND ccu.table_name = %s;
            ''', (table_name,))
            for row in c_cursor.fetchall():
                children.append(f"  - {row[0]} (via {row[1]})")
    except Exception:
        pass

    parent_str = "\n".join(parents) if parents else "  - None (Top-level table)"
    child_str = "\n".join(children) if children else "  - None (Leaf table)"

    return f"PARENTS (Tables this table depends on):\n{parent_str}\n\nCHILDREN (Tables that depend on this table):\n{child_str}"


@tool
def describe_tables(table_names: list[str] = None, table_name: str = None) -> str:
    """Use this tool to get table business descriptions, column types, sample rows, and linear parent/child relationships in a single call."""
    
    if table_names is None:
        table_names = []
    if table_name:
        table_names.append(table_name)
        
    cleaned_names = []
    for t in table_names:
        try:
            # Parse the string as a SQL Table identifier to robustly extract the raw name
            table_ast = sqlglot.parse_one(t, read="postgres", into=exp.Table)
            if table_ast and table_ast.name:
                cleaned_names.append(table_ast.name.lower())
        except Exception:
            pass

    valid_tables = [t for t in cleaned_names if t in validator.allowed_tables]
    if not valid_tables:
        return "Error: None of the requested tables are allowed or exist."

    discovery = SQLDiscoveryTool(
        connection_string=DATABASE_URL,
        schema_name="public",
        include_tables=valid_tables,
        sample_rows_in_table_info=3,
    )
    raw_schema = discovery.get_formatted_schema()

    output_sections = []
    for t in valid_tables:
        desc = get_table_description(t)
        hierarchy = get_table_hierarchy_info(t)
        output_sections.append(f"==================================================\nTABLE: {t}\nDESCRIPTION: {desc}\n--------------------------------------------------\n{hierarchy}\n==================================================")

    enhanced_info = "\n\n".join(output_sections)
    return f"{enhanced_info}\n\nCOLUMNS & SAMPLE ROWS:\n{raw_schema}"


@tool
def get_schema_minimap() -> str:
    """Use this tool to get a JSON node graph of how the database tables are connected to each other via foreign keys, along with table descriptions."""
    try:
        with pool.connection() as conn:
            cursor = conn.execute('''
                SELECT
                    tc.table_name, 
                    ccu.table_name AS foreign_table_name
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='public';
            ''')
            fks = cursor.fetchall()
            
            allowed = validator.allowed_tables
            connections = {t: {"description": get_table_description(t), "foreign_keys": []} for t in allowed}
            for row in fks:
                t, ft = row[0], row[1]
                if t in allowed and ft in allowed:
                    if ft not in connections[t]["foreign_keys"]:
                        connections[t]["foreign_keys"].append(ft)
            return json.dumps(connections, indent=2)
    except Exception as e:
        return f"Error building minimap: {e}"

# Add to the exported tools list
tools = [query_database, describe_tables, get_schema_minimap]

