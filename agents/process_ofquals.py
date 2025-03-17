"""
Command example:
cd agents
python process_ofquals.py --batch-size 1000 --workers 10
"""
import sqlite3
import argparse
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from utils import extract_text
from extractor import ofqual_agent

# Define PDF directory at the top for easy modification
#ofqual_dir = r"C:\Users\smrit\Downloads\ofqual_set3_7"
# ofqual_dir = r"/Users/adityachhabra/Documents/ofqual"
ofqual_dir = r"F:\ofqual"

load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def extract_and_save_ofqual(basename, pdf_dir, db_path="ofqual_details.db"):
    # Construct full path
    full_path = os.path.join(pdf_dir, basename)
    
    logger.debug(f"Processing file: {basename}")
    text = extract_text(full_path)
    res = ofqual_agent.run_sync(user_prompt="Extract OfQual Details from the following PDF:\n\n" + text)
    json_data = res.data.model_dump_json()

    # Connect to SQLite DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Update json_data column in SQLite using basename
    cursor.execute('''
    UPDATE ofqual_pdfs
    SET json_data = ?
    WHERE filepath = ?
    ''', (json_data, basename))

    conn.commit()
    conn.close()


# Fetch random filepaths with empty JSON data
def fetch_empty_filepaths(db_path="ofqual_details.db", limit=5):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT filepath FROM ofqual_pdfs
    WHERE json_data = '{}'
    ORDER BY RANDOM()
    LIMIT ?
    ''', (limit,))
    filepaths = [row[0] for row in cursor.fetchall()]
    conn.close()
    logger.info(f"Fetched {len(filepaths)} filepaths with empty JSON data")
    return filepaths


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process OfQual PDFs and extract data')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of PDFs to process (default: 100)')
    parser.add_argument('--workers', type=int, default=10, help='Number of worker threads (default: 10)')
    parser.add_argument('--db-path', type=str, default="ofqual_details.db", help='Path to SQLite database (default: ofqual_details.db)')
    args = parser.parse_args()
    
    # Log the parameters
    logger.info(f"Starting processing with batch_size={args.batch_size}, workers={args.workers}, pdf_dir={ofqual_dir}")
    
    # Fetch filepaths (these are now basenames)
    pdf_basenames = fetch_empty_filepaths(db_path=args.db_path, limit=args.batch_size)
    
    if not pdf_basenames:
        logger.warning("No files found to process")
        return
    
    results = {}
    completed = 0
    
    # Process concurrently
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_pdf = {executor.submit(extract_and_save_ofqual, basename, ofqual_dir, args.db_path): basename 
                        for basename in pdf_basenames}
        total = len(future_to_pdf)
        
        logger.info(f"Processing {total} files with {args.workers} workers")
        
        for future in as_completed(future_to_pdf):
            basename = future_to_pdf[future]
            try:
                future.result()  # result is not captured here, as the DB is already updated
                results[basename] = "Success"
                completed += 1
                logger.info(f"Completed {completed}/{total} files. Successfully processed: {basename}")
            except Exception as e:
                results[basename] = str(e)
                logger.error(f"Error processing {basename}: {str(e)}")
                completed += 1
                logger.info(f"Completed {completed}/{total} files")
    
    # Log summary
    success_count = list(results.values()).count("Success")
    logger.info(f"Processing complete. {success_count}/{total} files processed successfully")


if __name__ == "__main__":
    main()
