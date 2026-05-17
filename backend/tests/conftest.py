from pathlib import Path

import pytest

from app.database.repository import set_db_path


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path):
    set_db_path(tmp_path / "test.db")
    yield
