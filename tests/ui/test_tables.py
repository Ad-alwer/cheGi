import pytest
from unittest.mock import patch
from chegi.ui.tables import display_results_table

def test_display_results_table_empty():
    """Ensure rendering does not crash when provided with an empty dataset."""
    with patch("chegi.ui.tables.console.print") as mock_print:
        display_results_table([])
        mock_print.assert_called()

def test_display_results_table_with_data():
    """Verify table rendering logic executes properly with valid datasets."""
    sample_data = [
        {"file": "src/main.py", "issue": "Hardcoded secret", "severity": "High"},
        {"file": "src/utils.py", "issue": "Debug flag enabled", "severity": "Medium"}
    ]
    
    with patch("chegi.ui.tables.console.print") as mock_print:
        display_results_table(sample_data)
        mock_print.assert_called()
