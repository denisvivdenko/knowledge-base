import numpy as np
from model2vec import StaticModel

from knowledge_base.domain.question import Question

DEFAULT_MODEL_NAME = "minishlab/potion-retrieval-32M"
DEFAULT_SIMILARITY_THRESHOLD = 0.15


class SemanticSearch:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self._model = StaticModel.from_pretrained(model_name)
        self._similarity_threshold = similarity_threshold
        self._questions: list[Question] = []
        self._vectors: np.ndarray | None = None

    def add(self, questions: list[Question]) -> None:
        if not questions:
            return
        vectors = self._embed([question.content for question in questions])
        self._questions.extend(questions)
        self._vectors = vectors if self._vectors is None else np.vstack([self._vectors, vectors])

    def search(self, topic: str) -> list[Question]:
        if self._vectors is None:
            return []
        query_vector = self._embed([topic])[0]
        similarities = self._vectors @ query_vector
        ranked = sorted(zip(self._questions, similarities), key=lambda pair: pair[1], reverse=True)
        return [question for question, similarity in ranked if similarity >= self._similarity_threshold]

    def drop(self) -> None:
        self._questions = []
        self._vectors = None

    def _embed(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(texts)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
