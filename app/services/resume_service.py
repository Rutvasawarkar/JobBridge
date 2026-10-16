import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RESUMES_DIR = BASE_DIR / "data" / "resumes"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def get_resumes_dir():
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    return RESUMES_DIR


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_resume_file(user_id, file_storage):
    """
    Validate, sanitize, and save an uploaded resume file.
    Returns (success: bool, result_or_error: str, original_filename: str)
    """
    if not file_storage or not file_storage.filename:
        return False, "No file selected.", ""

    filename = file_storage.filename
    if not is_allowed_file(filename):
        return False, "Invalid file format. Only PDF, DOCX, and TXT files are allowed.", filename

    # Check file size by seeking
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)

    if size > MAX_FILE_SIZE:
        return False, f"File exceeds maximum allowed size of 5 MB ({round(size / (1024*1024), 1)} MB uploaded).", filename

    if size == 0:
        return False, "The uploaded file is empty.", filename

    resumes_folder = get_resumes_dir()
    clean_name = secure_filename(filename)
    unique_prefix = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
    saved_filename = f"{unique_prefix}_{clean_name}"
    target_path = resumes_folder / saved_filename

    file_storage.save(str(target_path))
    return True, str(target_path), clean_name
