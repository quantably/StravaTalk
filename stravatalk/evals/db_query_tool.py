#!/usr/bin/env python3
"""
Simple tool for running arbitrary SQL queries against the StravaTalk database.
Usage: python db_query_tool.py "SELECT * FROM activities LIMIT 5;"
"""

import sys
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

def run_query(sql_query, return_dataframe=True):
    """Execute SQL query and return results."""
    load_dotenv()
    
    try:
        # Connect to database
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        
        if return_dataframe:
            # Use pandas for nice formatting
            df = pd.read_sql(sql_query, conn)
            conn.close()
            return df
        else:
            # Use raw cursor for non-SELECT queries
            cursor = conn.cursor()
            cursor.execute(sql_query)
            
            if sql_query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                conn.close()
                return results, columns
            else:
                conn.commit()
                conn.close()
                return f"Query executed successfully. Rows affected: {cursor.rowcount}"
                
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python db_query_tool.py 'SQL_QUERY'")
        print("\nExamples:")
        print("python db_query_tool.py 'SELECT COUNT(*) FROM activities;'")
        print("python db_query_tool.py 'SELECT * FROM activities WHERE type = \"Run\" LIMIT 5;'")
        print("python db_query_tool.py 'SHOW TABLES;'")
        return
    
    sql_query = sys.argv[1]
    print(f"Executing: {sql_query}")
    print("-" * 50)
    
    result = run_query(sql_query)
    
    if result is not None:
        if isinstance(result, pd.DataFrame):
            print(result.to_string(index=False))
        else:
            print(result)
    else:
        print("Query failed.")

if __name__ == "__main__":
    main()