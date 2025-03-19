import sqlite3
import pandas as pd
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def export_markschemes(db_path="ofqual_units.db", output_path="ofqual_markscheme.csv"):
    """Export all records with non-null markschemes from SQLite to CSV."""
    try:
        # Connect to SQLite DB
        logger.info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        
        # Query to get all records where markscheme is not null
        query = """
        SELECT *
        FROM ofqual_units
        WHERE markscheme IS NOT NULL
        """
        
        # Read into pandas DataFrame
        logger.info("Fetching records with non-null markschemes...")
        df = pd.read_sql_query(query, conn)
        
        # Close connection
        conn.close()
        
        # Get count of records
        record_count = len(df)
        logger.info(f"Found {record_count} records with markschemes")
        
        if record_count == 0:
            logger.warning("No records found with markschemes")
            return
        
        # Save to CSV
        logger.info(f"Saving to CSV: {output_path}")
        df.to_csv(output_path, index=False)
        logger.info(f"Successfully exported {record_count} records to {output_path}")
        
    except Exception as e:
        logger.error(f"Error exporting markschemes: {str(e)}")
        raise

if __name__ == "__main__":
    export_markschemes() 