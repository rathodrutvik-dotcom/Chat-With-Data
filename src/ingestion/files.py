import os
import shutil
import uuid
import datetime

import gradio as gr

from config.settings import DATA_DIR, IST


def create_unique_filename() -> str:
    """Generate a unique filename with timestamp."""
    uid = uuid.uuid4()
    timestamp = datetime.datetime.now(IST).strftime("%d-%m-%Y-%H-%M-%S")
    return f"file-{uid}-{timestamp}"


def validate_and_save_files(uploaded_files):
    """Validate and save uploaded files to the data directory."""
    if not uploaded_files:
        raise gr.Error("⚠️ Please upload at least one file.")

    file_group_name = create_unique_filename()
    saved_files = []

    for idx, file in enumerate(uploaded_files, start=1):
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in [".pdf", ".docx", ".xlsx"]:
            raise gr.Error(f"❌ Unsupported file type: {ext}. Only PDF, DOCX, XLSX are allowed.")

        save_path = DATA_DIR / f"{file_group_name}-{idx}{ext}"
        try:
            shutil.copyfile(file.name, str(save_path))
            saved_files.append(str(save_path))
        except Exception as exc:  # pylint: disable=broad-except
            raise gr.Error(f"❌ Error saving file: {str(exc)}") from exc

    return saved_files, file_group_name


__all__ = ["create_unique_filename", "validate_and_save_files"]
