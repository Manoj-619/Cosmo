import os

def list_files_exclude(startpath, exclude_dirs):
    """
    Generate a tree structure of files and directories, excluding specified directories.
    
    :param startpath: Root directory to start generating the tree.
    :param exclude_dirs: List of directories to exclude (relative to startpath).
    """
    for root, dirs, files in os.walk(startpath):
        # Modify `dirs` in-place to exclude desired directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        # Calculate the indentation level
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        
        # Print the folder name
        print(f"{indent}{os.path.basename(root)}/")
        
        # Print the files in the current folder
        subindent = ' ' * 4 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")

# Example usage
if __name__ == "__main__":
    # Replace with your desired folder path
    folder_path = r"C:\Users\amith\Kenpath\zavmo-api"
    
    # Replace with the folders you want to exclude
    exclude_folders = ["zavenv", "__pycache__"]
    
    list_files_exclude(folder_path, exclude_folders)
