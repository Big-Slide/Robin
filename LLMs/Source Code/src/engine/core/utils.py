from pathlib import Path
from typing import Optional, List
import os
import json
import re
import base64
import PyPDF2
import mimetypes


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


def add_file_to_message(human_message: List, file_path: str, file_content_bytes):
    """
    Add various file types to the conversation message

    Args:
        human_message: List to append the file content to
        file_path: Path to the file (for MIME type detection)
        file_content_bytes: Raw bytes of the file content
    """

    # Get MIME type from file extension
    mime_type, _ = mimetypes.guess_type(file_path)
    file_extension = Path(file_path).suffix.lower()

    # Convert bytes to base64
    file_content_b64 = base64.b64encode(file_content_bytes).decode("utf-8")

    # Handle different file types
    if mime_type and mime_type.startswith("image/"):
        # Images - use image_url format
        human_message.append(
            {
                "type": "image_url",
                "image_url": f"data:{mime_type};base64,{file_content_b64}",
            }
        )

    elif file_extension in [".pdf"]:
        # PDFs - use document format
        human_message.append(
            {
                "type": "document",
                "document": {"format": "pdf", "data": file_content_b64},
            }
        )

    elif file_extension in [
        ".txt",
        ".md",
        ".py",
        ".js",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
    ]:
        # Text-based files - decode and include as text
        try:
            text_content = file_content_bytes.decode("utf-8")
            human_message.append(
                {
                    "type": "text",
                    "text": f"File: {Path(file_path).name}\n```{file_extension[1:]}\n{text_content}\n```",
                }
            )
        except UnicodeDecodeError:
            # If text decoding fails, treat as binary
            human_message.append(
                {
                    "type": "document",
                    "document": {
                        "format": "binary",
                        "name": Path(file_path).name,
                        "data": file_content_b64,
                    },
                }
            )

    elif file_extension in [".csv"]:
        # CSV files - include as text with special formatting
        try:
            csv_content = file_content_bytes.decode("utf-8")
            human_message.append(
                {
                    "type": "text",
                    "text": f"CSV File: {Path(file_path).name}\n```csv\n{csv_content}\n```",
                }
            )
        except UnicodeDecodeError:
            human_message.append(
                {
                    "type": "document",
                    "document": {
                        "format": "csv",
                        "name": Path(file_path).name,
                        "data": file_content_b64,
                    },
                }
            )

    elif file_extension in [".xlsx", ".xls"]:
        # Excel files
        human_message.append(
            {
                "type": "document",
                "document": {
                    "format": "excel",
                    "name": Path(file_path).name,
                    "data": file_content_b64,
                },
            }
        )

    elif file_extension in [".docx", ".doc"]:
        # Word documents
        human_message.append(
            {
                "type": "document",
                "document": {
                    "format": "word",
                    "name": Path(file_path).name,
                    "data": file_content_b64,
                },
            }
        )

    elif file_extension in [".pptx", ".ppt"]:
        # PowerPoint presentations
        human_message.append(
            {
                "type": "document",
                "document": {
                    "format": "powerpoint",
                    "name": Path(file_path).name,
                    "data": file_content_b64,
                },
            }
        )

    else:
        # Generic file handling
        human_message.append(
            {
                "type": "document",
                "document": {
                    "format": "binary",
                    "name": Path(file_path).name,
                    "mime_type": mime_type,
                    "data": file_content_b64,
                },
            }
        )


def delete_file(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)
