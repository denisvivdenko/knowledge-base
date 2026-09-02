from pathlib import Path

from knowledge_base.domain.question import Question


class QuestionRepository:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def save(self, questions: list[Question]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_path.open("a") as f:
            for question in questions:
                f.write(question.model_dump_json())
                f.write("\n")

    def load_all(self) -> list[Question]:
        if not self._file_path.exists():
            return []
        with self._file_path.open("r") as f:
            return [Question.model_validate_json(line) for line in f if line.strip()]

    def drop(self) -> None:
        self._file_path.unlink(missing_ok=True)
