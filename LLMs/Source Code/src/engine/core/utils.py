from pathlib import Path
from typing import Optional
import os
import json
import re
import base64
import PyPDF2


async def get_pdf_content(filepath: str) -> str:
    pdf_content = ""
    with open(filepath, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            pdf_content += page.extract_text() + "\n"
    return pdf_content


async def img_to_b64(filepath: str) -> str:
    with open(filepath, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_json_from_response(response_text: str):
    """
    Extracts a JSON object from a text response.
    Assumes the JSON is enclosed in curly braces {} or a code block.
    """
    try:
        # Try to directly parse if the whole response is JSON
        return json.dumps(json.loads(response_text), separators=(",", ":"))
    except json.JSONDecodeError:
        # Fallback: Extract the first JSON-like block from the text
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            json_str = json_match.group()
            try:
                return json.dumps(json.loads(json_str), separators=(",", ":"))
            except json.JSONDecodeError as e:
                raise ValueError("Found JSON block but could not parse it.") from e
        raise ValueError("No JSON object found in the response.")


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


def delete_file(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)
