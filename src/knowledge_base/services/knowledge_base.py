from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository


class KnowledgeBase:
    def __init__(self, repository: QuestionRepository) -> None:
        self._repository = repository

    def add_questions(self, questions: list[Question]) -> None:
        self._repository.save(questions)

    def sample_by_topic(self, topic: str) -> list[Question]:
        return [
            question
            for question in self._repository.load_all()
            if topic.lower() in question.content.lower()
        ]
