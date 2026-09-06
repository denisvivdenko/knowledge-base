from pathlib import Path

from knowledge_base.domain.question import Question
from knowledge_base.services.semantic_search import SemanticSearch


class QuestionRepository:
    def __init__(self, file_path: Path, search: SemanticSearch) -> None:
        self._file_path = file_path
        self._search = search
        self._search.add(self.load_all())

    def save(self, questions: list[Question]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_path.open("a") as f:
            for question in questions:
                f.write(question.model_dump_json())
                f.write("\n")
        self._search.add(questions)

    def load_all(self) -> list[Question]:
        if not self._file_path.exists():
            return []
        with self._file_path.open("r") as f:
            return [Question.model_validate_json(line) for line in f if line.strip()]

    def search_by_topic(self, topic: str) -> list[Question]:
        return self._search.search(topic)

    def drop(self) -> None:
        self._file_path.unlink(missing_ok=True)
        self._search.drop()
