import os
import logging
from typing import Union, List

logger = logging.getLogger(__name__)

def cleanup_file(file_paths: Union[str, List[str]]):
    """
    Clean up one or more files efficiently.
    Args:
        file_paths: Single file path or list of file paths to clean up
    """
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temp file {file_path}: {e}")
