import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.sheets_logger import (
    _ensure_headers,
    _next_serial,
    _write_local_backup,
    log_query,
)


def test_write_local_backup():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = Path(tmp_dir) / "rag_query_log.jsonl"
        with patch("src.sheets_logger._BACKUP_DIR", Path(tmp_dir)), patch(
            "src.sheets_logger._BACKUP_FILE", tmp_file
        ):
            record = {
                "timestamp": "2026-08-08T12:00:00",
                "question": "What is T1D?",
                "answer": "Type 1 Diabetes...",
                "citations": ["Doc1.pdf, p.1"],
            }
            _write_local_backup(record)

            assert tmp_file.exists()
            lines = tmp_file.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["question"] == "What is T1D?"


def test_ensure_headers_empty_sheet():
    mock_ws = MagicMock()
    mock_ws.acell.return_value.value = None

    _ensure_headers(mock_ws)

    mock_ws.append_row.assert_called_once_with(
        [
            "S. No.",
            "Question",
            "Answer",
            "Citations",
            "Completeness",
            "Correctness",
            "Relevancy",
            "Remarks",
        ],
        value_input_option="RAW",
    )


def test_next_serial_calculation():
    mock_ws = MagicMock()
    mock_ws.col_values.return_value = ["S. No.", "1", "2", "3"]

    next_num = _next_serial(mock_ws)
    assert next_num == 4


def test_log_query_creates_local_backup_and_background_thread():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = Path(tmp_dir) / "rag_query_log.jsonl"
        with patch("src.sheets_logger._BACKUP_DIR", Path(tmp_dir)), patch(
            "src.sheets_logger._BACKUP_FILE", tmp_file
        ), patch("src.sheets_logger._append_to_sheet") as mock_append:

            log_query(
                question="What are symptoms of hypo?",
                answer="Shakiness, sweating...",
                citations=["Guidelines.pdf, p.4"],
            )

            # Assert local backup written
            assert tmp_file.exists()
            lines = tmp_file.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["question"] == "What are symptoms of hypo?"

            # Give thread a brief moment to run
            mock_append.assert_called_once_with(
                "What are symptoms of hypo?",
                "Shakiness, sweating...",
                "Guidelines.pdf, p.4",
            )
