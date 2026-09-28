TABLE_DESCRIPTIONS = {
    "_01_user_management_account": "Account organization details and tenant account metadata.",
    "_01_user_management_accountmember": "Maps users to accounts, defining membership roles, permissions, grower numbers, and contract details.",
    "_01_user_management_userprofile": "Core user profile information including names, emails, and global user IDs.",
    "_01_user_management_employeeprofile": "Employee-specific profile details linked to user accounts.",
    "_02_site_site": "Physical land/farm site definitions, geographic locations, and site metadata.",
    "_02_site_sitecrop": "Crops associated with specific physical sites (farm locations).",
    "_02_site_sitecropvariety": "Specific crop varieties planted at a site crop location.",
    "_03_crop_customcrop": "Tenant-defined custom crop definitions.",
    "_03_crop_customvariety": "Tenant-defined custom crop variety definitions.",
    "_03_crop_globalcrop": "System-wide global master database of standard crop species.",
    "_03_crop_globalvariety": "System-wide global master database of standard crop varieties.",
    "_04_equipment_equipment": "Machinery, spray rigs, tractors, and application equipment assigned to accounts.",
    "_04_equipment_equipmenttype": "Categories and types of farm/spray equipment.",
    "_06_chemical_chemical": "Global database of agricultural chemicals, active ingredients, and EPA registration metadata.",
    "_06_chemical_chemicalcropdata": "Chemical safety & compliance data including Restricted Entry Intervals (REI), Pre-Harvest Intervals (PHI), and application rates.",
    "_07_spraycard_spraycard": "Main record for chemical application spray cards, including status ('assigned', 'active', 'completed'), planned date, applicator, and notes.",
    "_07_spraycard_spraycardcropselection": "Junction table detailing specific crops and target pests selected for treatment in a spray card.",
    "_07_spraycard_spraycardsitetreatment": "Junction table detailing specific farm sites/fields treated in a spray card, including area treated.",
    "_07_spraycard_spraycardchemical": "Junction table detailing specific chemicals applied in a spray card, including chemical application rates and dosages.",
    "_07_spraycard_spraycardequipment": "Junction table detailing equipment and machinery assigned to a spray card.",
    "_07_spraycard_cropgrowthstage": "Crop growth stage tracking linked to account members and spray applications."
}

def get_table_description(table_name: str) -> str:
    """Return the plain-English business description for a table."""
    clean_name = table_name.lower().replace("public.", "").replace("ai_views.", "")
    return TABLE_DESCRIPTIONS.get(clean_name, "No description available.")

from functools import lru_cache
from src.agent_traccrop.db import pool

@lru_cache(maxsize=1)
def get_table_catalog_summary(allowed_tables: tuple) -> str:
    """Dynamically queries database columns and formats a clean catalog with descriptions and column lists for the starting prompt."""
    table_columns = {}
    try:
        with pool.connection() as conn:
            cursor = conn.execute('''
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_schema='public' 
                ORDER BY table_name, ordinal_position;
            ''')
            for t, c in cursor.fetchall():
                if t in allowed_tables:
                    table_columns.setdefault(t, []).append(c)
    except Exception:
        pass

    lines = []
    for t in sorted(allowed_tables):
        desc = get_table_description(t)
        cols = table_columns.get(t, [])
        col_str = f" Columns: [{', '.join(cols)}]" if cols else ""
        lines.append(f"- `{t}`: {desc}{col_str}")
    return "\n".join(lines)
