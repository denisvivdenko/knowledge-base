from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.semantic_search import SemanticSearch


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


@pytest.fixture(scope="session")
def search() -> SemanticSearch:
    return SemanticSearch()


@pytest.fixture(autouse=True)
def _drop_search_index(search):
    yield
    search.drop()


def test_load_all_returns_empty_list_when_no_file_exists(repo_path, search):
    repo = QuestionRepository(repo_path, search)

    assert repo.load_all() == []


def test_save_then_load_all_round_trips_questions(repo_path, search):
    repo = QuestionRepository(repo_path, search)
    questions = [make_question(), make_question()]

    repo.save(questions)

    assert repo.load_all() == questions


def test_save_appends_without_overwriting_existing_questions(repo_path, search):
    repo = QuestionRepository(repo_path, search)
    first_batch = [make_question()]
    second_batch = [make_question()]

    repo.save(first_batch)
    repo.save(second_batch)

    assert repo.load_all() == first_batch + second_batch


def test_data_persists_across_separate_repository_instances(repo_path, search):
    QuestionRepository(repo_path, search).save([make_question()])

    loaded = QuestionRepository(repo_path, search).load_all()

    assert len(loaded) == 1


def test_drop_removes_all_saved_questions(repo_path, search):
    repo = QuestionRepository(repo_path, search)
    repo.save([make_question()])

    repo.drop()

    assert repo.load_all() == []


def test_drop_is_a_noop_when_no_file_exists(repo_path, search):
    repo = QuestionRepository(repo_path, search)

    repo.drop()

    assert repo.load_all() == []


def test_search_by_topic_returns_questions_matching_the_topic_after_save(repo_path, search):
    repo = QuestionRepository(repo_path, search)
    databricks_question = make_question(content="What is a Databricks cluster policy?")
    postgres_question = make_question(content="What is a Postgres B-tree index?")

    repo.save([databricks_question, postgres_question])

    assert repo.search_by_topic("databricks") == [databricks_question]


def test_search_by_topic_reflects_questions_saved_through_a_separate_repository_instance(repo_path, search):
    databricks_question = make_question(content="What is a Databricks cluster policy?")
    QuestionRepository(repo_path, SemanticSearch()).save([databricks_question])

    repo = QuestionRepository(repo_path, search)

    assert repo.search_by_topic("databricks") == [databricks_question]
