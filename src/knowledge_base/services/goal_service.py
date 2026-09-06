from uuid import UUID

from knowledge_base.domain.goal import Goal
from knowledge_base.domain.question import Question
from knowledge_base.repositories.goal_repository import GoalRepository
from knowledge_base.services.knowledge_base import KnowledgeBase


class GoalService:
    def __init__(self, repository: GoalRepository, knowledge_base: KnowledgeBase) -> None:
        self._repository = repository
        self._knowledge_base = knowledge_base

    def add_goal(self, content: str) -> Goal:
        goal = Goal(content=content)
        self._repository.save(goal)
        return goal

    def list_goals(self) -> list[Goal]:
        return sorted(self._repository.load_all(), key=lambda g: g.created_at, reverse=True)

    def get_goal(self, goal_id: UUID) -> Goal | None:
        return next((g for g in self._repository.load_all() if g.id == goal_id), None)

    def retrieve_questions(self, goal_id: UUID) -> list[Question]:
        goal = self.get_goal(goal_id)
        if goal is None:
            return []
        return self._knowledge_base.retrieve_by_topic(goal.content)
