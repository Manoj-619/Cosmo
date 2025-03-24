import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def monitor_markschemes(db_path="ofqual_units.db"):
    """
    Monitor the progress of markscheme generation by counting:
    - Total records in the database
    - Records with completed markschemes
    - Records with incomplete markschemes
    """
    try:
        # Connect to SQLite DB
        logger.info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM ofqual_units")
        total_records = cursor.fetchone()[0]
        
        # Count completed markschemes (non-null)
        cursor.execute("SELECT COUNT(*) FROM ofqual_units WHERE markscheme IS NOT NULL")
        completed_markschemes = cursor.fetchone()[0]
        
        # Calculate incomplete markschemes
        incomplete_markschemes = total_records - completed_markschemes
        
        # Calculate completion percentage
        completion_percentage = (completed_markschemes / total_records * 100) if total_records > 0 else 0
        
        # Close connection
        conn.close()
        
        # Print results
        logger.info("=== Markscheme Generation Progress ===")
        logger.info(f"Total records: {total_records}")
        logger.info(f"Completed markschemes: {completed_markschemes}")
        logger.info(f"Incomplete markschemes: {incomplete_markschemes}")
        logger.info(f"Completion percentage: {completion_percentage:.2f}%")
        logger.info("=====================================")
        
        return {
            "total": total_records,
            "completed": completed_markschemes,
            "incomplete": incomplete_markschemes,
            "percentage_complete": completion_percentage
        }
        
    except Exception as e:
        logger.error(f"Error monitoring markschemes: {str(e)}")
        raise

if __name__ == "__main__":
    monitor_markschemes()
