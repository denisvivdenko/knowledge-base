from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.knowledge_base import KnowledgeBase


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
def kb(tmp_path):
    repo = QuestionRepository(tmp_path / "questions.jsonl")
    return KnowledgeBase(repo)


def test_sample_by_topic_returns_added_questions_matching_the_topic(kb):
    databricks_question = make_question(content="What is a Databricks cluster policy?")
    postgres_question = make_question(content="What is a Postgres B-tree index?")

    kb.add_questions(questions=[databricks_question, postgres_question])

    assert kb.sample_by_topic(topic="databricks") == [databricks_question]


def test_sample_by_topic_returns_empty_list_when_nothing_matches(kb):
    kb.add_questions(questions=[make_question(content="What is a Postgres B-tree index?")])

    assert kb.sample_by_topic(topic="databricks") == []
