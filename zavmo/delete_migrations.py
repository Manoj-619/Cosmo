import os

def delete_migrations():
    project_dir = os.getcwd()
    deleted_files_count = 0

    # Check and delete db.sqlite3 if it exists
    db_file_path = os.path.join(project_dir, 'db.sqlite3')
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
        print(f"Deleted database file: {db_file_path}")

    for root, dirs, files in os.walk(project_dir):
        if 'migrations' in dirs:
            migrations_dir = os.path.join(root, 'migrations')
            for file_name in os.listdir(migrations_dir):
                if file_name != '__init__.py' and file_name.endswith('.py'):
                    file_path = os.path.join(migrations_dir, file_name)
                    os.remove(file_path)
                    deleted_files_count += 1
                    print(f"Deleted: {file_path}")

    print(f"Total migration files deleted: {deleted_files_count}")

if __name__ == '__main__':
    delete_migrations()
