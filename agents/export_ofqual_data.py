import sqlite3
import argparse
import logging
import json
import pandas as pd
from typing import List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from _types import Ofqual, InvalidQualification

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def fetch_non_empty_ofqual_docs(db_path="ofqual_details.db"):
    """Fetch all non-empty JSON data from the ofqual_pdfs table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT filepath, json_data FROM ofqual_pdfs
    WHERE json_data != '{}'
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    logger.info(f"Fetched {len(results)} non-empty ofqual documents")
    return results


def parse_ofqual_doc(doc_data):
    """Parse the JSON data and determine if it's a valid Ofqual document"""
    filepath, json_data = doc_data
    
    try:
        # Parse the JSON data
        data = json.loads(json_data)
        
        # Check if it's an Ofqual or InvalidQualification
        if "rationale" in data:
            # This is an InvalidQualification
            return None
        elif "id" in data and "units" in data:
            # This is a valid Ofqual document
            ofqual = Ofqual.model_validate(data)
            return ofqual
        else:
            logger.warning(f"Unknown document type for {filepath}")
            return None
    except Exception as e:
        logger.error(f"Error parsing document {filepath}: {str(e)}")
        return None


def process_ofqual_docs(docs, max_workers=10):
    """Process ofqual documents in parallel"""
    valid_ofquals = []
    processed = 0
    total = len(docs)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_doc = {executor.submit(parse_ofqual_doc, doc): doc for doc in docs}
        
        for future in as_completed(future_to_doc):
            doc = future_to_doc[future]
            processed += 1
            
            try:
                ofqual = future.result()
                if ofqual:
                    valid_ofquals.append(ofqual)
                    logger.info(f"Processed {processed}/{total}. Valid Ofqual: {ofqual.id}")
                else:
                    logger.info(f"Processed {processed}/{total}. Invalid document: {doc[0]}")
            except Exception as e:
                logger.error(f"Error processing document {doc[0]}: {str(e)}")
    
    logger.info(f"Found {len(valid_ofquals)} valid Ofqual documents out of {total} total documents")
    return valid_ofquals


def create_ofqual_csv(ofquals: List[Ofqual], output_path="ofqual_unit_details.csv"):
    """Create a CSV file with all ofqual unit level details, including qualification_id"""
    if not ofquals:
        logger.warning("No valid Ofqual documents found. CSV not created.")
        return
    
    # Create a list to store all unit data
    all_units_data = []
    
    # Process each Ofqual document
    for ofqual in ofquals:
        try:
            # Get the table for this Ofqual
            df = ofqual.get_table()
            
            # Add qualification_id to each unit's data
            df['qualification_id'] = ofqual.id

            # Convert learning_outcomes from list of objects to string
            df['learning_outcomes'] = df['learning_outcomes'].apply(lambda x: f"{json.dumps(x)}")

            # Reorder columns as per the required order, removing 'units'
            df = df[['qualification_id', 'overview', 'id', 'title', 'description', 'learning_outcomes']]
            
            # Convert DataFrame to list of dictionaries
            units_data = df.to_dict('records')
            all_units_data.extend(units_data)
        except Exception as e:
            logger.error(f"Error processing Ofqual {ofqual.id}: {str(e)}")
    
    # Create a DataFrame from all unit data
    if all_units_data:
        df = pd.DataFrame(all_units_data)
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        logger.info(f"CSV file created successfully: {output_path}")
        logger.info(f"Total units exported: {len(all_units_data)}")
    else:
        logger.warning("No unit data found. CSV not created.")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Export Ofqual data to CSV')
    parser.add_argument('--db-path', type=str, default="ofqual_details.db", 
                        help='Path to SQLite database (default: ofqual_details.db)')
    parser.add_argument('--output', type=str, default="ofqual_unit_details.csv", 
                        help='Output CSV file path (default: ofqual_unit_details.csv)')
    parser.add_argument('--workers', type=int, default=10, 
                        help='Number of worker threads (default: 10)')
    args = parser.parse_args()
    
    # Log the parameters
    logger.info(f"Starting export with db_path={args.db_path}, output={args.output}, workers={args.workers}")
    
    # Fetch non-empty ofqual documents
    docs = fetch_non_empty_ofqual_docs(db_path=args.db_path)
    
    if not docs:
        logger.warning("No documents found to process")
        return
    
    # Process the documents
    valid_ofquals = process_ofqual_docs(docs, max_workers=args.workers)
    
    # Create the CSV file
    create_ofqual_csv(valid_ofquals, output_path=args.output)
    
    logger.info("Export process completed")


if __name__ == "__main__":
    main() 