import os
import sqlite3
from dotenv import load_dotenv

#ofqual_dir = r"C:\Users\smrit\Downloads\ofqual_set3_7"
ofqual_dir = r"/Users/adityachhabra/Documents/ofqual"

load_dotenv()

from utils import walk_dir

# Get current PDF file paths
pdf_filepaths = walk_dir(ofqual_dir, extension="pdf")

# SQLite database setup
db_path = "ofqual_details.db"

# Connect to SQLite DB
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get existing filepaths from the database
cursor.execute('SELECT filepath FROM ofqual_pdfs')
existing_filepaths = {row[0] for row in cursor.fetchall()}

# Find new filepaths
new_filepaths = [fp for fp in pdf_filepaths if fp not in existing_filepaths]

# Insert only new file paths
for fp in new_filepaths:
    cursor.execute('''
    INSERT INTO ofqual_pdfs (filepath, json_data)
    VALUES (?, '{}')
    ''', (fp,))

# Commit changes and close connection
conn.commit()
conn.close()

print("Database update completed successfully.")
print(f"Added {len(new_filepaths)} new PDF paths to the database.") 