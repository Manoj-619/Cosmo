"""
Command example:
cd agents
python process_ofquals.py --batch-size 1000 --workers 10
"""
import json
import sqlite3
import argparse
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from generator import markscheme_agent

load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def format_text(record):
# Ofqual specific columns
    ofqual_fields = ["ofqual_id", "overview", "sector_subject_area", "qualification_type", "qualification_level", "total_credits", "guided_learning_hours", "total_qualification_time"]

# Unit specific columns
    unit_fields = ["unit_id", "unit_title", "unit_description", "unit_learning_outcomes"]

    ofqual_string = "\n".join([f"{field.capitalize().replace('_', ' ')}: {record[field]}" for field in ofqual_fields])
    unit_string = "\n".join([f"{field.capitalize().replace('_', ' ')}: {record[field]}" for field in unit_fields])
    return f"**Ofqual Details:**\n{ofqual_string}\n\n**Unit Details:**\n{unit_string}"

def generate_and_save_markscheme(record, db_path="ofqual_units.db"):
    # Construct full pat
    text       = format_text(record)
    res        = markscheme_agent.run_sync(user_prompt="Generate a markscheme for the following unit:\n\n" + text)
    markschemes      = [ms.model_dump_json() for ms in res.data] # List of MarkSchemeItems
    markschemes_json = json.dumps(markschemes)

    
    # Connect to SQLite DB
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Update json_data column in SQLite using basename
    cursor.execute('''
    UPDATE ofqual_units
    SET markscheme = ?
    WHERE unit_uid = ?
    ''', (markschemes_json, record["unit_uid"]))

    conn.commit()
    conn.close()


# Fetch random filepaths with empty JSON data

def fetch_null_markschemes(db_path="ofqual_units.db", limit=5):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM ofqual_units
    WHERE markscheme IS NULL
    ORDER BY RANDOM()
    LIMIT ?
    ''', (limit,))
    
    # Get column names from cursor description
    columns = [i[0] for i in cursor.description]
    
    # Fetch all rows and convert to list of dictionaries
    rows = cursor.fetchall()
    units = [dict(zip(columns, row)) for row in rows]
    
    print(f"Fetched {len(units)} units with empty markscheme")
    
    # Close connection
    conn.close()
    
    return units


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate markschemes for OFQUAL units')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of OFQUAL units to process (default: 100)')
    parser.add_argument('--workers', type=int, default=10, help='Number of worker threads (default: 10)')
    parser.add_argument('--db-path', type=str, default="ofqual_units.db", help='Path to SQLite database (default: ofqual_units.db)')
    args = parser.parse_args()
    
    # Log the parameters
    logger.info(f"Starting processing with batch_size={args.batch_size}, workers={args.workers}, db_path={args.db_path}")
    
    # Fetch units with empty markscheme
    records = fetch_null_markschemes(db_path=args.db_path, limit=args.batch_size)
    
    if not records:
        logger.warning("No units found to process")
        return

    logger.info(f"Processing {len(records)} units with {args.workers} workers")
    
    results = {}
    completed = 0
    
    # Process concurrently
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_record = {executor.submit(generate_and_save_markscheme, record, args.db_path): record
                        for record in records}
        total = len(future_to_record)
        
        logger.info(f"Processing {total} units with {args.workers} workers")
        
        for future in as_completed(future_to_record):
            record = future_to_record[future]
            try:
                future.result()  # result is not captured here, as the DB is already updated
                results[record["unit_uid"]] = "Success"
                completed += 1
                logger.info(f'Completed {completed}/{total} units. Successfully processed: {record["unit_uid"]}')
            except Exception as e:
                results[record["unit_uid"]] = str(e)
                logger.error(f'Error processing {record["unit_uid"]}: {str(e)}')
                completed += 1
                logger.info(f'Completed {completed}/{total} units')
    
    # Log summary
    success_count = list(results.values()).count("Success")
    logger.info(f'Processing complete. {success_count}/{total} units processed successfully')


if __name__ == "__main__":
    main()
