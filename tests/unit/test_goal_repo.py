from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_base.domain.goal import Goal
from knowledge_base.repositories.goal_repository import GoalRepository


def make_goal(**overrides) -> Goal:
    defaults = dict(
        id=uuid4(),
        content="Learn how retries are handled",
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Goal(**defaults)


@pytest.fixture
def repo_path(tmp_path):
    return tmp_path / "goals.jsonl"


def test_load_all_returns_empty_list_when_no_file_exists(repo_path):
    repo = GoalRepository(repo_path)

    assert repo.load_all() == []


def test_save_then_load_all_round_trips_the_goal(repo_path):
    repo = GoalRepository(repo_path)
    goal = make_goal()

    repo.save(goal)

    assert repo.load_all() == [goal]


def test_save_appends_without_overwriting_existing_goals(repo_path):
    repo = GoalRepository(repo_path)
    first_goal = make_goal()
    second_goal = make_goal()

    repo.save(first_goal)
    repo.save(second_goal)

    assert repo.load_all() == [first_goal, second_goal]


def test_data_persists_across_separate_repository_instances(repo_path):
    GoalRepository(repo_path).save(make_goal())

    loaded = GoalRepository(repo_path).load_all()

    assert len(loaded) == 1


def test_drop_removes_all_saved_goals(repo_path):
    repo = GoalRepository(repo_path)
    repo.save(make_goal())

    repo.drop()

    assert repo.load_all() == []


def test_drop_is_a_noop_when_no_file_exists(repo_path):
    repo = GoalRepository(repo_path)

    repo.drop()

    assert repo.load_all() == []
