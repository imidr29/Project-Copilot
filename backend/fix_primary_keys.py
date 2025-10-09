import re

input_file = "mydb.sql"
output_file = "mydb_fixed.sql"

with open(input_file, "r") as f:
    sql = f.read()

def add_primary_key(match):
    table_def = match.group(0)
    # Skip tables that already have a PRIMARY KEY
    if "PRIMARY KEY" in table_def.upper():
        return table_def
    # Insert a synthetic primary key as the first column
    table_def_fixed = re.sub(
        r"CREATE TABLE\s+(`?\w+`?)\s*\(",
        r"CREATE TABLE \1 (\n  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,",
        table_def,
        flags=re.IGNORECASE
    )
    return table_def_fixed

# Match each CREATE TABLE ... (...); block (simplified)
pattern = re.compile(r"CREATE TABLE.*?\);", re.DOTALL | re.IGNORECASE)
fixed_sql = pattern.sub(add_primary_key, sql)

with open(output_file, "w") as f:
    f.write(fixed_sql)

print(f"Fixed dump saved to {output_file}")

