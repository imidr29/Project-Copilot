import pandas as pd
import numpy as np
import re
import logging
from typing import Dict, Any, List, Tuple
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVProcessor:
    def __init__(self, database: Database):
        self.db = database
    
    def process_csv(self, file_path: str, table_name: str, upload_mode: str, has_headers: bool = True) -> Dict[str, Any]:
        """
        Process CSV file and upload to database
        
        Args:
            file_path: Path to CSV file
            table_name: Name for the database table
            upload_mode: 'structured' or 'unstructured'
            has_headers: Whether first row contains headers
            
        Returns:
            Dict with processing results
        """
        try:
            # Read CSV file
            if has_headers:
                df = pd.read_csv(file_path)
            else:
                df = pd.read_csv(file_path, header=None)
                # Generate column names
                df.columns = [f'column_{i+1}' for i in range(len(df.columns))]
            
            logger.info(f"Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
            
            # Clean data if unstructured
            if upload_mode == 'unstructured':
                df = self._clean_data(df)
                logger.info("Data cleaning completed")
            
            # Validate and prepare data for database
            df = self._prepare_for_database(df)
            
            # Check for duplicate data in existing tables
            duplicate_check = self._check_for_duplicate_data(df, table_name)
            if duplicate_check['is_duplicate']:
                logger.info(f"Duplicate data found in table: {duplicate_check['existing_table']}")
                return {
                    "success": True,
                    "table_name": duplicate_check['existing_table'],
                    "rows_inserted": 0,
                    "columns": list(df.columns),
                    "data_types": {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()},
                    "cleaning_applied": upload_mode == 'unstructured',
                    "duplicate_detected": True,
                    "message": f"Data already exists in table '{duplicate_check['existing_table']}'. No new table created.",
                    "result": f"Duplicate data found in existing table: {duplicate_check['existing_table']}"
                }
            
            # Check for tables with same schema that can be combined
            schema_match_check = self._check_for_schema_match(df, table_name)
            if schema_match_check['can_combine']:
                logger.info(f"Schema match found with table: {schema_match_check['existing_table']}")
                return self._combine_tables(df, schema_match_check['existing_table'], table_name, upload_mode)
            
            # Create table and insert data
            result = self._create_table_and_insert(df, table_name)
            
            return {
                "success": True,
                "table_name": table_name,
                "rows_inserted": len(df),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()},
                "cleaning_applied": upload_mode == 'unstructured',
                "result": result
            }
            
        except Exception as e:
            logger.error(f"CSV processing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply basic data cleaning and preprocessing
        """
        logger.info("Starting data cleaning process...")
        
        # Make a copy to avoid modifying original
        df_clean = df.copy()
        
        # 1. Handle missing values
        df_clean = self._handle_missing_values(df_clean)
        
        # 2. Clean text data
        df_clean = self._clean_text_data(df_clean)
        
        # 3. Standardize date formats
        df_clean = self._standardize_dates(df_clean)
        
        # 4. Clean numeric data
        df_clean = self._clean_numeric_data(df_clean)
        
        # 5. Remove duplicates
        df_clean = self._remove_duplicates(df_clean)
        
        # 6. Clean column names
        df_clean.columns = self._clean_column_names(df_clean.columns)
        
        logger.info(f"Data cleaning completed. Final shape: {df_clean.shape}")
        return df_clean
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset"""
        logger.info("Handling missing values...")
        
        for column in df.columns:
            if df[column].dtype == 'object':  # Text columns
                # Fill with 'Unknown' for text columns
                df[column] = df[column].fillna('Unknown')
            else:  # Numeric columns
                # Fill with median for numeric columns
                if not df[column].isna().all():
                    median_val = df[column].median()
                    df[column] = df[column].fillna(median_val)
                else:
                    df[column] = df[column].fillna(0)
        
        return df
    
    def _clean_text_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize text data"""
        logger.info("Cleaning text data...")
        
        for column in df.columns:
            if df[column].dtype == 'object':
                # Convert to string and strip whitespace
                df[column] = df[column].astype(str).str.strip()
                
                # Remove extra whitespace
                df[column] = df[column].str.replace(r'\s+', ' ', regex=True)
                
                # Standardize case for common fields
                if any(keyword in column.lower() for keyword in ['status', 'state', 'type', 'category']):
                    df[column] = df[column].str.title()
                
                # Clean special characters
                df[column] = df[column].str.replace(r'[^\w\s\-\.]', '', regex=True)
        
        return df
    
    def _standardize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize date formats"""
        logger.info("Standardizing date formats...")
        
        date_columns = []
        for column in df.columns:
            if df[column].dtype == 'object':
                # Check if column contains date-like data
                sample_values = df[column].dropna().head(10)
                if len(sample_values) > 0:
                    # Try to parse as dates
                    try:
                        pd.to_datetime(sample_values, errors='raise')
                        date_columns.append(column)
                    except:
                        pass
        
        for column in date_columns:
            try:
                df[column] = pd.to_datetime(df[column], errors='coerce')
                logger.info(f"Converted {column} to datetime")
            except:
                logger.warning(f"Could not convert {column} to datetime")
        
        return df
    
    def _clean_numeric_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean numeric data"""
        logger.info("Cleaning numeric data...")
        
        for column in df.columns:
            if df[column].dtype == 'object':
                # Try to convert to numeric
                try:
                    # Remove common non-numeric characters
                    cleaned = df[column].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
                    numeric_series = pd.to_numeric(cleaned, errors='coerce')
                    
                    # If more than 50% of values are numeric, convert the column
                    if not numeric_series.isna().sum() / len(numeric_series) > 0.5:
                        df[column] = numeric_series
                        logger.info(f"Converted {column} to numeric")
                except:
                    pass
        
        return df
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows"""
        logger.info("Removing duplicates...")
        initial_rows = len(df)
        df = df.drop_duplicates()
        removed = initial_rows - len(df)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate rows")
        return df
    
    def _clean_column_names(self, columns: List[str]) -> List[str]:
        """Clean column names for database compatibility"""
        logger.info("Cleaning column names...")
        
        cleaned_columns = []
        for col in columns:
            # Convert to lowercase
            clean_col = str(col).lower()
            
            # Replace spaces and special characters with underscores
            clean_col = re.sub(r'[^\w]', '_', clean_col)
            
            # Remove multiple underscores
            clean_col = re.sub(r'_+', '_', clean_col)
            
            # Remove leading/trailing underscores
            clean_col = clean_col.strip('_')
            
            # Ensure column name is not empty and doesn't start with number
            if not clean_col or clean_col[0].isdigit():
                clean_col = f'col_{clean_col}' if clean_col else 'unnamed_column'
            
            # Ensure uniqueness
            original_col = clean_col
            counter = 1
            while clean_col in cleaned_columns:
                clean_col = f"{original_col}_{counter}"
                counter += 1
            
            cleaned_columns.append(clean_col)
        
        return cleaned_columns
    
    def _prepare_for_database(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame for database insertion"""
        logger.info("Preparing data for database...")
        
        # Handle infinite values
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Convert datetime to string for database storage
        for column in df.columns:
            if df[column].dtype == 'datetime64[ns]':
                df[column] = df[column].dt.strftime('%Y-%m-%d %H:%M:%S')
                df[column] = df[column].fillna('')
        
        # Convert NaN to None for database compatibility
        df = df.where(pd.notnull(df), None)
        
        return df
    
    def _create_table_and_insert(self, df: pd.DataFrame, table_name: str) -> str:
        """Create table and insert data"""
        logger.info(f"Creating table {table_name} and inserting data...")
        
        try:
            # Create table
            self.db.create_table_from_dataframe(df, table_name)
            
            # Insert data
            rows_inserted = self.db.insert_dataframe(df, table_name)
            
            logger.info(f"Successfully inserted {rows_inserted} rows into {table_name}")
            return f"Table {table_name} created with {rows_inserted} rows"
            
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise Exception(f"Failed to create table or insert data: {str(e)}")
    
    def _check_for_duplicate_data(self, df: pd.DataFrame, proposed_table_name: str) -> Dict[str, Any]:
        """
        Check if the data in the DataFrame already exists in any existing table
        
        Args:
            df: DataFrame to check
            proposed_table_name: Name of the proposed new table
            
        Returns:
            Dict with duplicate check results
        """
        try:
            # Get all existing tables
            tables_query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()"
            existing_tables = self.db.execute_query(tables_query)
            
            logger.info(f"Checking for duplicates against {len(existing_tables)} existing tables")
            
            # Convert DataFrame to a standardized format for comparison
            df_normalized = self._normalize_dataframe_for_comparison(df)
            
            for table_row in existing_tables:
                table_name = table_row['TABLE_NAME']
                
                # Skip if it's the same table name (user might be re-uploading)
                if table_name.lower() == proposed_table_name.lower():
                    continue
                
                try:
                    # Get table structure
                    columns_query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' AND COLUMN_NAME != 'id' ORDER BY ORDINAL_POSITION"
                    table_columns = self.db.execute_query(columns_query)
                    table_column_names = [col['COLUMN_NAME'] for col in table_columns]
                    
                    # Check if column count matches
                    if len(table_column_names) != len(df_normalized.columns):
                        continue
                    
                    # Check if column names match (case-insensitive)
                    df_columns_lower = [col.lower() for col in df_normalized.columns]
                    table_columns_lower = [col.lower() for col in table_column_names]
                    
                    if sorted(df_columns_lower) != sorted(table_columns_lower):
                        continue
                    
                    # Get all data from existing table
                    select_query = f"SELECT * FROM `{table_name}` ORDER BY id"
                    existing_data = self.db.execute_query(select_query)
                    
                    # Check if row count matches
                    if len(existing_data) != len(df_normalized):
                        continue
                    
                    # Compare data row by row
                    if self._compare_data_content(df_normalized, existing_data, table_column_names):
                        logger.info(f"Exact duplicate found in table: {table_name}")
                        return {
                            'is_duplicate': True,
                            'existing_table': table_name,
                            'match_type': 'exact_data_match'
                        }
                        
                except Exception as e:
                    logger.warning(f"Error checking table {table_name}: {e}")
                    continue
            
            logger.info("No duplicate data found")
            return {
                'is_duplicate': False,
                'existing_table': None,
                'match_type': None
            }
            
        except Exception as e:
            logger.error(f"Error in duplicate check: {e}")
            return {
                'is_duplicate': False,
                'existing_table': None,
                'match_type': None
            }
    
    def _normalize_dataframe_for_comparison(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame for comparison by:
        1. Converting all values to strings
        2. Handling NaN values consistently
        3. Sorting columns alphabetically
        """
        try:
            # Create a copy
            df_normalized = df.copy()
            
            # Convert all values to strings and handle NaN
            for col in df_normalized.columns:
                df_normalized[col] = df_normalized[col].astype(str)
                df_normalized[col] = df_normalized[col].replace('nan', 'None')
                df_normalized[col] = df_normalized[col].replace('None', '')
            
            # Sort columns alphabetically
            df_normalized = df_normalized.reindex(sorted(df_normalized.columns), axis=1)
            
            # Sort rows by all columns to ensure consistent order
            df_normalized = df_normalized.sort_values(by=list(df_normalized.columns)).reset_index(drop=True)
            
            return df_normalized
            
        except Exception as e:
            logger.error(f"Error normalizing DataFrame: {e}")
            return df
    
    def _compare_data_content(self, df_normalized: pd.DataFrame, existing_data: List[Dict], table_columns: List[str]) -> bool:
        """
        Compare the normalized DataFrame with existing database data
        
        Args:
            df_normalized: Normalized DataFrame
            existing_data: List of dictionaries from database
            table_columns: Column names from existing table
            
        Returns:
            True if data matches exactly, False otherwise
        """
        try:
            # Convert existing data to DataFrame for easier comparison
            existing_df = pd.DataFrame(existing_data)
            
            # Remove 'id' column if it exists
            if 'id' in existing_df.columns:
                existing_df = existing_df.drop('id', axis=1)
            
            # Normalize existing data the same way
            existing_df_normalized = self._normalize_dataframe_for_comparison(existing_df)
            
            # Check if DataFrames are identical
            if df_normalized.shape != existing_df_normalized.shape:
                return False
            
            # Compare each cell
            for i in range(len(df_normalized)):
                for col in df_normalized.columns:
                    if str(df_normalized.iloc[i][col]) != str(existing_df_normalized.iloc[i][col]):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error comparing data content: {e}")
            return False
    
    def _check_for_schema_match(self, df: pd.DataFrame, proposed_table_name: str) -> Dict[str, Any]:
        """
        Check if the DataFrame schema matches any existing table schema
        
        Args:
            df: DataFrame to check
            proposed_table_name: Name of the proposed new table
            
        Returns:
            Dict with schema match results
        """
        try:
            # Get all existing tables
            tables_query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()"
            existing_tables = self.db.execute_query(tables_query)
            
            logger.info(f"Checking for schema matches against {len(existing_tables)} existing tables")
            
            for table_row in existing_tables:
                table_name = table_row['TABLE_NAME']
                
                # Skip if it's the same table name
                if table_name.lower() == proposed_table_name.lower():
                    continue
                
                try:
                    # Get table structure
                    columns_query = f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' AND COLUMN_NAME != 'id' ORDER BY ORDINAL_POSITION"
                    table_columns = self.db.execute_query(columns_query)
                    table_column_info = {col['COLUMN_NAME']: col['DATA_TYPE'] for col in table_columns}
                    table_column_names = list(table_column_info.keys())
                    
                    # Check if column count matches
                    if len(table_column_names) != len(df.columns):
                        continue
                    
                    # Check if column names match (case-insensitive)
                    df_columns_lower = [col.lower() for col in df.columns]
                    table_columns_lower = [col.lower() for col in table_column_names]
                    
                    if sorted(df_columns_lower) != sorted(table_columns_lower):
                        continue
                    
                    # Check if data types are compatible
                    if self._are_data_types_compatible(df, table_column_info):
                        logger.info(f"Schema match found with table: {table_name}")
                        return {
                            'can_combine': True,
                            'existing_table': table_name,
                            'match_type': 'schema_match'
                        }
                        
                except Exception as e:
                    logger.warning(f"Error checking table {table_name}: {e}")
                    continue
            
            logger.info("No schema matches found")
            return {
                'can_combine': False,
                'existing_table': None,
                'match_type': None
            }
            
        except Exception as e:
            logger.error(f"Error in schema match check: {e}")
            return {
                'can_combine': False,
                'existing_table': None,
                'match_type': None
            }
    
    def _are_data_types_compatible(self, df: pd.DataFrame, table_column_info: Dict[str, str]) -> bool:
        """
        Check if DataFrame data types are compatible with existing table data types
        
        Args:
            df: DataFrame to check
            table_column_info: Dict mapping column names to SQL data types
            
        Returns:
            True if data types are compatible, False otherwise
        """
        try:
            for col in df.columns:
                # Find matching column (case-insensitive)
                matching_col = None
                for table_col in table_column_info.keys():
                    if col.lower() == table_col.lower():
                        matching_col = table_col
                        break
                
                if not matching_col:
                    return False
                
                # Get DataFrame column type
                df_dtype = str(df[col].dtype)
                sql_type = table_column_info[matching_col].upper()
                
                # Check compatibility
                if not self._is_type_compatible(df_dtype, sql_type):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking data type compatibility: {e}")
            return False
    
    def _is_type_compatible(self, pandas_type: str, sql_type: str) -> bool:
        """
        Check if pandas data type is compatible with SQL data type
        
        Args:
            pandas_type: Pandas data type string
            sql_type: SQL data type string
            
        Returns:
            True if compatible, False otherwise
        """
        # Convert pandas types to SQL-compatible types
        type_mapping = {
            'object': ['TEXT', 'VARCHAR', 'CHAR'],
            'int64': ['INT', 'INTEGER', 'BIGINT'],
            'int32': ['INT', 'INTEGER'],
            'float64': ['DOUBLE', 'FLOAT', 'DECIMAL'],
            'float32': ['FLOAT', 'DOUBLE'],
            'bool': ['BOOLEAN', 'TINYINT'],
            'datetime64[ns]': ['DATETIME', 'TIMESTAMP', 'DATE']
        }
        
        # Check if pandas type maps to SQL type
        for pandas_dtype, compatible_sql_types in type_mapping.items():
            if pandas_type.startswith(pandas_dtype):
                return any(sql_type.startswith(sql_t) for sql_t in compatible_sql_types)
        
        # Default: assume compatible if we can't determine
        return True
    
    def _combine_tables(self, df: pd.DataFrame, existing_table: str, proposed_table_name: str, upload_mode: str) -> Dict[str, Any]:
        """
        Combine the new DataFrame with an existing table
        
        Args:
            df: New DataFrame to combine
            existing_table: Name of existing table
            proposed_table_name: Originally proposed table name
            upload_mode: Upload mode for cleaning info
            
        Returns:
            Dict with combination results
        """
        try:
            logger.info(f"Combining data with existing table: {existing_table}")
            
            # Get existing table data to check for duplicates
            existing_data_query = f"SELECT * FROM `{existing_table}` ORDER BY id"
            existing_data = self.db.execute_query(existing_data_query)
            
            # Convert existing data to DataFrame
            existing_df = pd.DataFrame(existing_data)
            if 'id' in existing_df.columns:
                existing_df = existing_df.drop('id', axis=1)
            
            # Normalize both DataFrames for comparison
            df_normalized = self._normalize_dataframe_for_comparison(df)
            existing_df_normalized = self._normalize_dataframe_for_comparison(existing_df)
            
            # Find new rows (not in existing table)
            new_rows = []
            for i, new_row in df_normalized.iterrows():
                is_duplicate = False
                for j, existing_row in existing_df_normalized.iterrows():
                    if self._rows_are_equal(new_row, existing_row):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    new_rows.append(i)
            
            if not new_rows:
                logger.info("No new rows to add - all data already exists")
                return {
                    "success": True,
                    "table_name": existing_table,
                    "rows_inserted": 0,
                    "columns": list(df.columns),
                    "data_types": {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()},
                    "cleaning_applied": upload_mode == 'unstructured',
                    "combined_with_existing": True,
                    "message": f"All data already exists in table '{existing_table}'. No new rows added.",
                    "result": f"Data combined with existing table: {existing_table}"
                }
            
            # Insert only new rows
            new_df = df.iloc[new_rows].copy()
            rows_inserted = self.db.insert_dataframe(new_df, existing_table)
            
            logger.info(f"Successfully combined {rows_inserted} new rows into {existing_table}")
            
            return {
                "success": True,
                "table_name": existing_table,
                "rows_inserted": rows_inserted,
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()},
                "cleaning_applied": upload_mode == 'unstructured',
                "combined_with_existing": True,
                "message": f"Data combined with existing table '{existing_table}'. Added {rows_inserted} new rows.",
                "result": f"Data combined with existing table: {existing_table}"
            }
            
        except Exception as e:
            logger.error(f"Error combining tables: {e}")
            raise Exception(f"Failed to combine tables: {str(e)}")
    
    def _rows_are_equal(self, row1: pd.Series, row2: pd.Series) -> bool:
        """
        Check if two DataFrame rows are equal
        
        Args:
            row1: First row
            row2: Second row
            
        Returns:
            True if rows are equal, False otherwise
        """
        try:
            for col in row1.index:
                if str(row1[col]) != str(row2[col]):
                    return False
            return True
        except Exception as e:
            logger.error(f"Error comparing rows: {e}")
            return False
