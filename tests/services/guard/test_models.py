from chegi.services.guard.models import GuardScanResult


def test_guard_scan_result_safe():
    """Test creating a safe scan result."""
    result = GuardScanResult(is_safe=True, sensitive_files=[])

    assert result.is_safe is True
    assert result.sensitive_files == []


def test_guard_scan_result_unsafe():
    """Test creating an unsafe scan result with detected files."""
    files = [".env", "id_rsa", "config.json"]
    result = GuardScanResult(is_safe=False, sensitive_files=files)

    assert result.is_safe is False
    assert result.sensitive_files == files
    assert len(result.sensitive_files) == 3
