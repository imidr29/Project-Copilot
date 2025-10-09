import pymysql
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import os
from dotenv import load_dotenv
from contextlib import contextmanager
from config_loader import config

load_dotenv()

class Database:
    def __init__(self):
        self.config = config.get_database_config()

    @contextmanager
    def get_connection(self):
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()

    def test_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            return True
        except Exception as e:
            raise Exception(f"Database connection failed: {str(e)}")

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
        return results

    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                conn.commit()
        return affected_rows

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        query = f"DESCRIBE {table_name}"
        return self.execute_query(query)

    def get_all_tables(self) -> List[str]:
        query = "SHOW TABLES"
        results = self.execute_query(query)
        return [list(row.values())[0] for row in results]

    def get_database_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        tables = self.get_all_tables()
        schema = {}
        for table in tables:
            if not table.startswith('_'):
                schema[table] = self.get_table_schema(table)
        return schema

    def validate_sql(self, sql: str) -> bool:
        sql_clean = sql.replace("``````", "").strip()
        sql_lower = sql_clean.lower()
        if not sql_lower.startswith('select'):
            return False
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'create', 'truncate', 'grant', 'revoke']
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                return False
        return True

    def get_schema_description(self) -> str:
        return """
Database Schema for Mining and Factory Data (OEE Co-Pilot):

1. Factory_Equipment_Logs:
   - id (VARCHAR): Primary key (UUID)
   - equipment_name (VARCHAR): Equipment name
   - status (VARCHAR): 'Active' or 'Inactive'
   - date (DATE): Event date
   - start_date (DATE)
   - start_time (TIME)
   - end_date (DATE)
   - end_time (TIME)
   - duration_minutes (FLOAT)
   - alert (VARCHAR)
   - reason (TEXT)
   - issue (TEXT)
   - comment (TEXT)
   - date_created_at (DATE)
   - time_created_at (TIME)

2. Mining_Shift_Data:
   - Date (DATE)
   - Shift (VARCHAR)
   - Excavator (INT)
   - Dumper (INT)
   - `Trip Count for Mining` (INT)
   - `Trip Count for Reclaim` (INT)
   - `Total Trips` (INT)
   - `Qty m3` (FLOAT)
   - Grader (INT)
   - Dozer (INT)

3. Mining_Production_Site:
   - Date (DATE)
   - MiningBench (VARCHAR)
   - ExcavatorID (VARCHAR)
   - Destination (VARCHAR)
   - Specification (VARCHAR)
   - `Asset Name` (VARCHAR)
   - Production (FLOAT)
   - No_of_Trips (INT)
   - Production_Per_Trip (FLOAT)

IMPORTANT: Column names with spaces MUST be wrapped in backticks (`) in SQL queries.
Example: SELECT `Asset Name`, Production FROM Mining_Production_Site
"""

    def close(self):
        pass
    
    def create_table_from_dataframe(self, df: pd.DataFrame, table_name: str) -> None:
        """Create a table from a pandas DataFrame"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Drop table if it exists
                cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                
                # Create table with appropriate column types
                columns = []
                for col_name, dtype in df.dtypes.items():
                    if dtype == 'object':
                        # For text columns, use TEXT type
                        columns.append(f"`{col_name}` TEXT")
                    elif dtype in ['int64', 'int32']:
                        columns.append(f"`{col_name}` INT")
                    elif dtype in ['float64', 'float32']:
                        columns.append(f"`{col_name}` DOUBLE")
                    elif 'datetime' in str(dtype):
                        columns.append(f"`{col_name}` DATETIME")
                    else:
                        # Default to TEXT for unknown types
                        columns.append(f"`{col_name}` TEXT")
                
                create_table_sql = f"""
                CREATE TABLE `{table_name}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    {', '.join(columns)}
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
                
                cursor.execute(create_table_sql)
                conn.commit()
    
    def insert_dataframe(self, df: pd.DataFrame, table_name: str) -> int:
        """Insert DataFrame data into table"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Prepare data for insertion
                data_to_insert = []
                for _, row in df.iterrows():
                    # Convert row to tuple, handling None values
                    row_data = []
                    for value in row:
                        if pd.isna(value) or value is None:
                            row_data.append(None)
                        else:
                            row_data.append(value)
                    data_to_insert.append(tuple(row_data))
                
                # Create insert statement
                columns = ', '.join([f"`{col}`" for col in df.columns])
                placeholders = ', '.join(['%s'] * len(df.columns))
                insert_sql = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"
                
                # Insert data in batches
                batch_size = 1000
                total_inserted = 0
                
                for i in range(0, len(data_to_insert), batch_size):
                    batch = data_to_insert[i:i + batch_size]
                    cursor.executemany(insert_sql, batch)
                    total_inserted += len(batch)
                
                conn.commit()
                return total_inserted







