from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_base.domain.question import Question
from knowledge_base.repositories.goal_repository import GoalRepository
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.goal_service import GoalService
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
def goal_repository(tmp_path) -> GoalRepository:
    return GoalRepository(tmp_path / "goals.jsonl")


@pytest.fixture
def knowledge_base(tmp_path, search) -> KnowledgeBase:
    question_repository = QuestionRepository(tmp_path / "questions.jsonl", search)
    return KnowledgeBase(question_repository)


@pytest.fixture
def goal_service(goal_repository, knowledge_base) -> GoalService:
    return GoalService(goal_repository, knowledge_base)


def test_add_goal_saves_and_returns_the_goal(goal_service):
    goal = goal_service.add_goal(content="Learn how retries are handled")

    assert goal.content == "Learn how retries are handled"
    assert goal_service.list_goals() == [goal]


def test_list_goals_returns_empty_list_when_no_goals_saved(goal_service):
    assert goal_service.list_goals() == []


def test_list_goals_returns_goals_sorted_by_created_at_descending(goal_service):
    older = goal_service.add_goal(content="Older goal")
    newer = goal_service.add_goal(content="Newer goal")

    assert goal_service.list_goals() == [newer, older]


def test_get_goal_returns_the_matching_goal(goal_service):
    goal = goal_service.add_goal(content="Learn how retries are handled")

    assert goal_service.get_goal(goal.id) == goal


def test_get_goal_returns_none_when_goal_does_not_exist(goal_service):
    assert goal_service.get_goal(uuid4()) is None


def test_retrieve_questions_returns_questions_matching_the_goal_content(goal_service, knowledge_base):
    goal = goal_service.add_goal(content="Databricks cluster policies")
    databricks_question = make_question(content="What is a Databricks cluster policy?")
    postgres_question = make_question(content="What is a Postgres B-tree index?")
    knowledge_base.add_questions([databricks_question, postgres_question])

    retrieved_questions = goal_service.retrieve_questions(goal.id)

    assert retrieved_questions == [databricks_question]


def test_retrieve_questions_returns_empty_list_when_goal_does_not_exist(goal_service):
    assert goal_service.retrieve_questions(uuid4()) == []
