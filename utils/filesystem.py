from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, Iterator, Optional

LEGAL_FORMS = {"anonyme", "sarl", "suarl", "autre"}
ISSUE_FOLDER_PATTERN = re.compile(
    r"^(?P<issue_number>\d+)Journal_annonces(?P<issue_year>\d{4})$",
    re.IGNORECASE,
)


def iter_notice_files(dataset_root: str | Path) -> Iterator[Path]:
    """Yield all notice `.txt` files under the dataset root in sorted order."""
    root = Path(dataset_root)
    if not root.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {root}")

    for path in sorted(root.rglob("*.txt")):
        if path.is_file():
            yield path


def extract_metadata_from_path(
    file_path: str | Path, dataset_root: str | Path
) -> Optional[Dict[str, object]]:
    """Extract legal-form metadata from dataset-relative file path.

    Expected relative shape:
    <legal_form>/<year>/<issue_folder>/<source_file>
    """
    root = Path(dataset_root)
    path = Path(file_path)

    try:
        relative_path = path.relative_to(root)
    except ValueError:
        logging.warning("Skipping file outside dataset root: %s", path)
        return None

    parts = relative_path.parts
    if len(parts) != 4:
        logging.warning("Skipping malformed path (unexpected depth): %s", relative_path)
        return None

    legal_form, year_folder, issue_folder, source_file = parts
    legal_form = legal_form.lower()
    if legal_form not in LEGAL_FORMS:
        logging.warning("Skipping unknown legal form folder '%s' in %s", legal_form, relative_path)
        return None

    try:
        year = int(year_folder)
    except ValueError:
        logging.warning("Skipping malformed year folder '%s' in %s", year_folder, relative_path)
        return None

    issue_match = ISSUE_FOLDER_PATTERN.match(issue_folder)
    if issue_match is None:
        logging.warning("Skipping malformed issue folder '%s' in %s", issue_folder, relative_path)
        return None

    issue_number = int(issue_match.group("issue_number"))
    issue_year = int(issue_match.group("issue_year"))
    if issue_year != year:
        logging.info(
            "Year mismatch for %s: folder year=%s, issue year=%s; using folder year",
            relative_path,
            year,
            issue_year,
        )

    return {
        "legal_form": legal_form,
        "year": year,
        "issue_number": issue_number,
        "source_file": source_file,
    }
