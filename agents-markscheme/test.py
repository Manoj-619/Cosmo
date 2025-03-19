# Fetch random filepaths with empty JSON data
import sqlite3

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

if __name__ == "__main__":
    units = fetch_null_markschemes()
    print(units)