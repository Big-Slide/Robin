from pathlib import Path
from typing import Optional
import os


def delete_file(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)


def get_file_type(filename: str) -> Optional[str]:
    """
    Determine file type based on filename extension.

    Args:
        filename (str): The name of the file including extension

    Returns:
        Optional[str]: The file type category or None if unknown
    """

    # Extract file extension
    extension = Path(filename).suffix.lower()

    # File type mappings
    file_types = {
        # Images
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".bmp": "image",
        ".svg": "image",
        ".webp": "image",
        ".ico": "image",
        ".tiff": "image",
        ".tif": "image",
        # Documents
        ".pdf": "pdf",
        ".doc": "document",
        ".docx": "document",
        ".txt": "document",
        ".rtf": "document",
        ".odt": "document",
        ".xls": "spreadsheet",
        ".xlsx": "spreadsheet",
        ".csv": "spreadsheet",
        ".ppt": "presentation",
        ".pptx": "presentation",
        ".odp": "presentation",
        # Audio
        ".mp3": "audio",
        ".wav": "audio",
        ".flac": "audio",
        ".aac": "audio",
        ".ogg": "audio",
        ".wma": "audio",
        ".m4a": "audio",
        # Video
        ".mp4": "video",
        ".avi": "video",
        ".mkv": "video",
        ".mov": "video",
        ".wmv": "video",
        ".flv": "video",
        ".webm": "video",
        ".m4v": "video",
        # Archives
        ".zip": "archive",
        ".rar": "archive",
        ".7z": "archive",
        ".tar": "archive",
        ".gz": "archive",
        ".bz2": "archive",
        ".xz": "archive",
        # Code
        ".py": "code",
        ".js": "code",
        ".html": "code",
        ".css": "code",
        ".java": "code",
        ".cpp": "code",
        ".c": "code",
        ".php": "code",
        ".rb": "code",
        ".go": "code",
        ".rs": "code",
        ".ts": "code",
        # Executables
        ".exe": "executable",
        ".msi": "executable",
        ".deb": "executable",
        ".rpm": "executable",
        ".dmg": "executable",
        ".app": "executable",
    }

    return file_types.get(extension, None)
