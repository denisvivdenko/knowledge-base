from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.semantic_search import SemanticSearch


class KnowledgeBase:
    def __init__(self, repository: QuestionRepository, search: SemanticSearch) -> None:
        self._repository = repository
        self._search = search

    def add_questions(self, questions: list[Question]) -> None:
        self._repository.save(questions)
        self._search.add(questions)

    def retrieve_by_topic(self, topic: str) -> list[Question]:
        return self._search.search(topic)
