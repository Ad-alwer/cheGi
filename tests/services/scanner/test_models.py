from chegi.services.scanner.models import ScanOptions


def test_scan_options_defaults():
    """Test that ScanOptions initializes with correct default values."""
    options = ScanOptions(path="/tmp/test")
    
    assert options.path == "/tmp/test"
    assert options.max_depth is None
    assert options.workers == 2
    assert options.security is False
    assert options.dirty is False
    assert options.staged is False

def test_scan_options_custom_values():
    """Test that ScanOptions correctly assigns provided values."""
    options = ScanOptions(
        path="/custom/path",
        max_depth=5,
        workers=8,
        security=True,
        dirty=True,
        staged=True
    )
    
    assert options.path == "/custom/path"
    assert options.max_depth == 5
    assert options.workers == 8
    assert options.security is True
    assert options.dirty is True
    assert options.staged is True
