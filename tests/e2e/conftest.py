import os
from pathlib import Path

import pytest

from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.semantic_search import SemanticSearch

DEFAULT_DATA_DIR = Path.home() / ".knowledge-base"


@pytest.fixture(autouse=True)
def reset_knowledge_base():
    """Clears the questions saved by the real test server before each e2e"""
    data_dir = Path(os.environ.get("KNOWLEDGE_BASE_DATA_DIR", DEFAULT_DATA_DIR))
    QuestionRepository(data_dir / "questions.jsonl", SemanticSearch()).drop()
