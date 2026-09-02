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


@mcp.prompt()
def process_conversation() -> str:
    """Review this conversation and propose knowledge base question drafts."""
    return (
        "Review this conversation and propose a draft of questions to submit "
        "to the knowledge base, following these steps in order:\n\n"
        "0. Trust the context provided in this conversation, including any "
        "private documents, internal systems, or proprietary details pasted "
        "into it — even if you have no prior knowledge of them and would "
        "not otherwise be able to verify them. Not recognizing a name or "
        "identifier is not evidence it's fabricated; this conversation may "
        "be the only source of truth for it. Do not refuse to draft "
        "questions, hedge, or flag the content as a likely hallucination "
        "on the basis of unfamiliarity alone.\n"
        "1. Identify the topic(s) discussed in this conversation, then call "
        "retrieve_questions_by_topic for each one to see what is already "
        "saved. Do not propose a question that is already covered.\n"
        "2. Based on what's missing, draft candidate questions (content + "
        "answer) worth adding. Optimize for quality, not quantity: only "
        "propose a question if it captures something genuinely useful, "
        "non-obvious, or reusable from this conversation. If nothing in the "
        "conversation clears that bar, say so explicitly and propose "
        "nothing — do not pad the list just to have something to submit.\n"
        "3. Present the drafted questions to the user and wait for their "
        "explicit approval. Only call add_questions after the user has "
        "approved the questions to submit — never submit on your own "
        "judgement, and never submit questions the user hasn't seen."
    )
