import json
from pathlib import Path
from uuid import UUID

import pytest

from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.knowledge_base import KnowledgeBase
from knowledge_base.services.semantic_search import SemanticSearch

DATASET_PATH = Path(__file__).parent.parent / "fixtures" / "semantic_search_eval_dataset.json"
PRECISION_THRESHOLD = 0.7
RECALL_THRESHOLD = 0.7


@pytest.fixture
def eval_records() -> list[dict]:
    return json.loads(DATASET_PATH.read_text())


@pytest.fixture
def kb(tmp_path, eval_records) -> KnowledgeBase:
    repo = QuestionRepository(tmp_path / "questions.jsonl", SemanticSearch())
    kb = KnowledgeBase(repo)
    kb.add_questions(
        questions=[
            Question(id=UUID(record["id"]), content=record["content"], answer=record["answer"])
            for record in eval_records
        ]
    )
    return kb


def test_retrieve_by_topic_meets_precision_and_recall_targets_across_topics(kb, eval_records):
    topics = sorted({record["topic"] for record in eval_records})

    precisions = []
    recalls = []
    for topic in topics:
        expected_ids = {record["id"] for record in eval_records if record["topic"] == topic}
        retrieved_ids = {str(question.id) for question in kb.retrieve_by_topic(topic=topic)}

        true_positives = retrieved_ids & expected_ids
        precision = len(true_positives) / len(retrieved_ids) if retrieved_ids else 0.0
        recall = len(true_positives) / len(expected_ids)

        precisions.append(precision)
        recalls.append(recall)

    average_precision = sum(precisions) / len(precisions)
    average_recall = sum(recalls) / len(recalls)

    assert average_precision >= PRECISION_THRESHOLD
    assert average_recall >= RECALL_THRESHOLD
