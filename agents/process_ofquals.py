import sqlite3
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from utils import extract_text
from extractor import ofqual_agent

load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def extract_and_save_ofqual(fp, db_path="ofqual_details.db"):
    logger.debug(f"Processing file: {fp}")
    text = extract_text(fp)
    res = ofqual_agent.run_sync(user_prompt="Extract OfQual Details from the following PDF:\n\n" + text)
    json_data = res.data.model_dump_json()

    # Connect to SQLite DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Update json_data column in SQLite
    cursor.execute('''
    UPDATE ofqual_pdfs
    SET json_data = ?
    WHERE filepath = ?
    ''', (json_data, fp))

    conn.commit()
    conn.close()


# Fetch random filepaths with empty JSON data
def fetch_empty_filepaths(db_path="ofqual.db", limit=5):
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
    logger.info(f"Starting processing with batch_size={args.batch_size}, workers={args.workers}")
    
    # Fetch filepaths
    pdf_filepaths = fetch_empty_filepaths(db_path=args.db_path, limit=args.batch_size)
    
    if not pdf_filepaths:
        logger.warning("No files found to process")
        return
    
    results = {}
    completed = 0
    
    # Process concurrently
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_pdf = {executor.submit(extract_and_save_ofqual, fp, args.db_path): fp for fp in pdf_filepaths}
        total = len(future_to_pdf)
        
        logger.info(f"Processing {total} files with {args.workers} workers")
        
        for future in as_completed(future_to_pdf):
            pdf_fp = future_to_pdf[future]
            try:
                future.result()  # result is not captured here, as the DB is already updated
                results[pdf_fp] = "Success"
                completed += 1
                logger.info(f"Completed {completed}/{total} files. Successfully processed: {pdf_fp}")
            except Exception as e:
                results[pdf_fp] = str(e)
                logger.error(f"Error processing {pdf_fp}: {str(e)}")
                completed += 1
                logger.info(f"Completed {completed}/{total} files")
    
    # Log summary
    success_count = list(results.values()).count("Success")
    logger.info(f"Processing complete. {success_count}/{total} files processed successfully")


if __name__ == "__main__":
    main()
