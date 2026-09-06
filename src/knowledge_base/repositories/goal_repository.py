from pathlib import Path

from knowledge_base.domain.goal import Goal


class GoalRepository:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def save(self, goal: Goal) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_path.open("a") as f:
            f.write(goal.model_dump_json())
            f.write("\n")

    def load_all(self) -> list[Goal]:
        if not self._file_path.exists():
            return []
        with self._file_path.open("r") as f:
            return [Goal.model_validate_json(line) for line in f if line.strip()]

    def drop(self) -> None:
        self._file_path.unlink(missing_ok=True)
