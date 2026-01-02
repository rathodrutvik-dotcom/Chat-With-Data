from pathlib import Path

from config.settings import SYSTEM_PROMPT_DIR


def read_system_prompt(file_name: str) -> str:
    """Read system prompt from YAML file."""
    prompt_path = SYSTEM_PROMPT_DIR / file_name
    with open(prompt_path, "r") as file_handle:
        return file_handle.read().strip()


__all__ = ["read_system_prompt"]
