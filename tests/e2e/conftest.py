import os
from pathlib import Path

import pytest

from knowledge_base.repositories.question_repository import QuestionRepository

DEFAULT_DATA_DIR = Path.home() / ".knowledge-base"


@pytest.fixture(autouse=True)
def reset_knowledge_base():
    """Clears the questions saved by the real test server before each e2e
    test. Relies on mcp-server-test's data dir being bind-mounted to the same
    KNOWLEDGE_BASE_DATA_DIR this process sees (see docker-compose.yml and
    .env.test) — without that shared mount this would drop a different file
    than the one the running server reads from.
    """
    data_dir = Path(os.environ.get("KNOWLEDGE_BASE_DATA_DIR", DEFAULT_DATA_DIR))
    QuestionRepository(data_dir / "questions.jsonl").drop()
