from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.knowledge_base import KnowledgeBase
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


@pytest.fixture(scope="session")
def search() -> SemanticSearch:
    return SemanticSearch()


@pytest.fixture(autouse=True)
def _drop_search_index(search):
    yield
    search.drop()


@pytest.fixture
def kb(tmp_path, search) -> KnowledgeBase:
    repo = QuestionRepository(tmp_path / "questions.jsonl", search)
    return KnowledgeBase(repo)


def test_retrieve_by_topic_returns_added_questions_matching_the_topic(kb):
    databricks_question = make_question(content="What is a Databricks cluster policy?")
    postgres_question = make_question(content="What is a Postgres B-tree index?")
    kb.add_questions(questions=[databricks_question, postgres_question])

    retrieved_questions = kb.retrieve_by_topic(topic="databricks")

    assert retrieved_questions == [databricks_question]


def test_retrieve_by_topic_returns_empty_list_when_nothing_matches(kb):
    kb.add_questions(questions=[make_question(content="What is a Postgres B-tree index?")])

    retrieved_questions = kb.retrieve_by_topic(topic="databricks")

    assert retrieved_questions == []


def test_retrieve_by_topic_matches_paraphrased_questions_without_keyword_overlap(kb):
    kubernetes_question = make_question(
        content=(
            "How does a container orchestration platform gradually swap old application "
            "instances for new ones without downtime?"
        )
    )
    postgres_question = make_question(
        content=(
            "How does a relational database engine avoid blocking readers while writers "
            "are actively modifying rows?"
        )
    )
    kb.add_questions(questions=[kubernetes_question, postgres_question])

    retrieved_questions = kb.retrieve_by_topic(topic="kubernetes")

    assert retrieved_questions == [kubernetes_question]


def test_retrieve_by_topic_updates_the_index_incrementally_as_questions_are_added(kb):
    first_question = make_question(content="What is a Databricks cluster policy?")
    kb.add_questions(questions=[first_question])
    assert kb.retrieve_by_topic(topic="databricks") == [first_question]

    second_question = make_question(content="What is a Databricks SQL warehouse?")
    kb.add_questions(questions=[second_question])

    retrieved_questions = kb.retrieve_by_topic(topic="databricks")
    assert first_question in retrieved_questions
    assert second_question in retrieved_questions


def test_retrieve_by_topic_reflects_questions_saved_through_a_separate_repository_instance(tmp_path, search):
    questions_path = tmp_path / "questions.jsonl"
    databricks_question = make_question(content="What is a Databricks cluster policy?")
    QuestionRepository(questions_path, SemanticSearch()).save([databricks_question])
    kb = KnowledgeBase(QuestionRepository(questions_path, search))

    retrieved_questions = kb.retrieve_by_topic(topic="databricks")

    assert retrieved_questions == [databricks_question]
