from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository


class KnowledgeBase:
    def __init__(self, repository: QuestionRepository) -> None:
        self._repository = repository

    def add_questions(self, questions: list[Question]) -> None:
        self._repository.save(questions)

    def retrieve_by_topic(self, topic: str) -> list[Question]:
        return self._repository.search_by_topic(topic)
