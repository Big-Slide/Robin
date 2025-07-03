import uuid
import os


def generate_uuid():
    return str(uuid.uuid4())


def delete_file(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)


def validate_text(text: str):
    if len(text) > 1024:
        return False
    return True
