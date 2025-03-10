import os
import sqlite3
from dotenv import load_dotenv

ofqual_dir = r"C:\Users\smrit\Downloads\ofqual_set3_7"

load_dotenv()

from utils import walk_dir

# Get PDF file paths
pdf_filepaths = walk_dir(ofqual_dir)

# SQLite database setup
db_path = "ofqual_details.db"

# Connect to SQLite DB (creates db file if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table
cursor.execute('''
CREATE TABLE IF NOT EXISTS ofqual_pdfs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT UNIQUE,
    json_data TEXT DEFAULT '{}'
)
''')

# Insert file paths with empty JSON placeholders
for fp in pdf_filepaths:
    cursor.execute('''
    INSERT OR IGNORE INTO ofqual_pdfs (filepath, json_data)
    VALUES (?, '{}')
    ''', (fp,))

# Commit changes and close connection
conn.commit()
conn.close()

print("SQLite DB created and initialized successfully.")
print(f"Added {len(pdf_filepaths)} new PDF paths to the database.")