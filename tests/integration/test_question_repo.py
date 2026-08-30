from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository


def make_question(**overrides) -> Question:
    defaults = dict(
        id=uuid4(),
        content="What are the main components of a transformer?",
        answer="Attention, feed-forward layers, and normalization.",
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Question(**defaults)


@pytest.fixture
def repo_path(tmp_path):
    return tmp_path / "questions.jsonl"


def test_load_all_returns_empty_list_when_no_file_exists(repo_path):
    repo = QuestionRepository(repo_path)

    assert repo.load_all() == []


def test_save_then_load_all_round_trips_questions(repo_path):
    repo = QuestionRepository(repo_path)
    questions = [make_question(), make_question()]

    repo.save(questions)

    assert repo.load_all() == questions


def test_save_appends_without_overwriting_existing_questions(repo_path):
    repo = QuestionRepository(repo_path)
    first_batch = [make_question()]
    second_batch = [make_question()]

    repo.save(first_batch)
    repo.save(second_batch)

    assert repo.load_all() == first_batch + second_batch


def test_data_persists_across_separate_repository_instances(repo_path):
    QuestionRepository(repo_path).save([make_question()])

    loaded = QuestionRepository(repo_path).load_all()

    assert len(loaded) == 1
