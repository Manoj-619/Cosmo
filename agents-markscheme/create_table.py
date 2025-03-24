import os
import sqlite3
import pandas as pd
from pathlib import Path

# Path to the CSV file
csv_path = Path("../docs/rgcn/ofqual_units.csv")

# SQLite database setup
db_path = "ofqual_units.db"

# Read the CSV file
df = pd.read_csv(csv_path)
# Connect to SQLite DB (creates db file if it doesn't exist)
conn = sqlite3.connect(db_path)

# Add empty markscheme column to dataframe
df['markscheme'] = None

# Write to SQLite database
df.to_sql('ofqual_units', conn, if_exists='replace', index=False)

# Close connection
conn.close()

print("SQLite DB created and initialized successfully.")
print(f"Added {len(df)} rows to the database with an empty markscheme column.")
