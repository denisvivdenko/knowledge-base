import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.knowledge_base import KnowledgeBase

DEFAULT_DATA_DIR = Path.home() / ".knowledge-base"


def _data_dir() -> Path:
    return Path(os.environ.get("KNOWLEDGE_BASE_DATA_DIR", DEFAULT_DATA_DIR))


_repository = QuestionRepository(_data_dir() / "questions.jsonl")
_knowledge_base = KnowledgeBase(_repository)

mcp = FastMCP(
    "knowledge-base",
    host=os.environ.get("HOST", "127.0.0.1"),
    port=int(os.environ.get("PORT", "8000")),
)


class QuestionInput(BaseModel):
    content: str
    answer: str


@mcp.tool()
def add_questions(questions: list[QuestionInput]) -> dict:
    """Save a batch of questions to the knowledge base.

    Only call this after the user has explicitly approved the questions to
    save. Never submit questions on your own judgement that a conversation
    was worth keeping.
    """
    domain_questions = [Question(content=q.content, answer=q.answer) for q in questions]
    _knowledge_base.add_questions(domain_questions)
    return {"count": len(domain_questions)}


@mcp.tool()
def retrieve_questions_by_topic(topic: str) -> list[dict]:
    """Retrieve previously saved questions whose content matches the given topic."""
    matches = _knowledge_base.sample_by_topic(topic)
    return [question.model_dump(mode="json") for question in matches]
