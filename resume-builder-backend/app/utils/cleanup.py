import os

def cleanup_file(file_path: str):
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Failed to delete temp file {file_path}: {e}")
