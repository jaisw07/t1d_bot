"""
Google Sheets Logger for T1D RAG Bot Testing Framework.

Logs every query-answer pair to:
  1. A local JSONL file (always, as crash-safe backup)
  2. A Google Sheet (append-only, never overwrites existing rows)

Sheet columns:
  S. No. | Question | Answer | Citations | Completeness | Correctness | Relevancy | Remarks

The last 4 columns are left empty for medical professional grading.

Setup:
  1. Create a Google Cloud project and enable the Google Sheets API + Google Drive API.
  2. Create a service account and download its JSON key file.
  3. Set GOOGLE_SHEETS_CREDENTIALS_FILE=<path-to-key.json> in .env
  4. Set GOOGLE_SHEETS_SPREADSHEET_ID=<spreadsheet-id> in .env
  5. Share the Google Sheet with the service account email (Editor access).
"""

import os
import json
import logging
import datetime
from pathlib import Path
from threading import Thread

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Local JSONL backup (always written first for zero data loss)
# ---------------------------------------------------------------------------

_BACKUP_DIR = Path(__file__).resolve().parent.parent / "logs"
_BACKUP_FILE = _BACKUP_DIR / "rag_query_log.jsonl"


def _write_local_backup(record: dict) -> None:
    """Append a single record to the local JSONL backup file."""
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with open(_BACKUP_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Google Sheets client (lazy singleton)
# ---------------------------------------------------------------------------

_sheet = None


def _get_sheet():
    """Lazily initialize and return the gspread Worksheet object."""
    global _sheet
    if _sheet is not None:
        return _sheet

    from dotenv import load_dotenv
    load_dotenv()

    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

    if not creds_file or not spreadsheet_id:
        logger.warning(
            "Google Sheets logging disabled: set GOOGLE_SHEETS_CREDENTIALS_FILE "
            "and GOOGLE_SHEETS_SPREADSHEET_ID in .env"
        )
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        _sheet = spreadsheet.sheet1  # First worksheet
        logger.info("Google Sheets logger connected to spreadsheet %s", spreadsheet_id)

        # Ensure header row exists
        _ensure_headers(_sheet)
        return _sheet

    except Exception as e:
        logger.error("Failed to connect to Google Sheets: %s", e)
        return None


def _ensure_headers(ws) -> None:
    """Write the header row if the sheet is empty."""
    try:
        first_cell = ws.acell("A1").value
        if not first_cell:
            headers = [
                "S. No.",
                "Question",
                "Answer",
                "Citations",
                "Completeness",
                "Correctness",
                "Relevancy",
                "Remarks",
            ]
            ws.append_row(headers, value_input_option="RAW")
    except Exception as e:
        logger.error("Failed to write headers: %s", e)


def _next_serial(ws) -> int:
    """Determine the next serial number from existing rows."""
    try:
        col_a = ws.col_values(1)  # All values in column A
        # Filter out the header and empty cells, find max serial
        serials = []
        for val in col_a[1:]:  # skip header
            try:
                serials.append(int(val))
            except (ValueError, TypeError):
                continue
        return max(serials) + 1 if serials else 1
    except Exception:
        return 1


def _append_to_sheet(question: str, answer: str, citations: str) -> None:
    """Append a single row to the Google Sheet. Never overwrites existing data."""
    ws = _get_sheet()
    if ws is None:
        return

    try:
        serial = _next_serial(ws)
        row = [
            serial,       # S. No.
            question,     # Question
            answer,       # Answer
            citations,    # Citations
            "",           # Completeness  (grader fills)
            "",           # Correctness   (grader fills)
            "",           # Relevancy     (grader fills)
            "",           # Remarks       (grader fills)
        ]
        ws.append_row(row, value_input_option="RAW")
        logger.info("Logged query #%d to Google Sheet", serial)
    except Exception as e:
        logger.error("Failed to append row to Google Sheet: %s", e)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_query(question: str, answer: str, citations: list[str]) -> None:
    """
    Log a query-answer pair. Writes to local JSONL first (synchronous),
    then appends to Google Sheet in a background thread.

    Args:
        question:  The user's query string.
        answer:    The RAG-generated answer text.
        citations: List of citation strings (e.g. ["Doc.pdf, p.5", "Doc2.pdf, p.12"]).
    """
    citations_str = " | ".join(citations) if citations else ""
    timestamp = datetime.datetime.now().isoformat()

    # 1. Always write local backup first (synchronous, crash-safe)
    record = {
        "timestamp": timestamp,
        "question": question,
        "answer": answer,
        "citations": citations,
    }
    _write_local_backup(record)

    # 2. Append to Google Sheet in background (non-blocking for the UI)
    thread = Thread(
        target=_append_to_sheet,
        args=(question, answer, citations_str),
        daemon=True,
    )
    thread.start()
