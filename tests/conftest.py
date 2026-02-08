import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("")
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)
