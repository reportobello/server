import os
from pathlib import Path


ARTIFACT_DIR = Path(os.getenv("REPORTOBELLO_ARTIFACT_DIR", "/tmp")).resolve()  # noqa: S108

def get_file_artifact_path_from_hash(hash: str) -> Path:  # noqa: A002
    return FILE_ARTIFACT_DIR / hash[:2] / hash[2:4] / hash[4:6] / hash[6:]


PDF_ARTIFACT_DIR = ARTIFACT_DIR / "pdfs"
FILE_ARTIFACT_DIR = ARTIFACT_DIR / "files"

DOMAIN = os.getenv("REPORTOBELLO_DOMAIN", "")
assert DOMAIN

IS_LIVE_SITE = os.getenv("REPORTOBELLO_IS_LIVE_SITE") == "1"

ADMIN_API_KEY = os.getenv("REPORTOBELLO_ADMIN_API_KEY")
