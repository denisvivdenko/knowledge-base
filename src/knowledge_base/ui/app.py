import hmac
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import streamlit as st
from pydantic import BaseModel, Field

from knowledge_base.api.auth import hash_token
from knowledge_base.domain.question import Question
from knowledge_base.repositories.question_repository import QuestionRepository
from knowledge_base.services.semantic_search import SemanticSearch

DEFAULT_DATA_DIR = Path.home() / ".knowledge-base"


def _data_dir() -> Path:
    return Path(os.environ.get("KNOWLEDGE_BASE_DATA_DIR", DEFAULT_DATA_DIR))


def _authorized() -> bool:
    """Gate the console behind a password, checked by hash only.

    Skipped when CONSOLE_PASSWORD_HASH isn't set, so local dev (`make ui`)
    stays frictionless while the deployed /console route stays protected.
    """
    password_hash = os.environ.get("CONSOLE_PASSWORD_HASH")
    if not password_hash:
        return True

    if st.session_state.get("authorized"):
        return True

    password = st.text_input("Password", type="password")
    if password:
        if hmac.compare_digest(hash_token(password), password_hash):
            st.session_state["authorized"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


class Goal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GoalRepository:
    """Dummy JSONL-backed goal storage, to be replaced by a real service later."""

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


@st.cache_resource
def _get_semantic_search() -> SemanticSearch:
    return SemanticSearch()


def _question_repository(search: SemanticSearch) -> QuestionRepository:
    return QuestionRepository(_data_dir() / "questions.jsonl", search)


def _goal_repository() -> GoalRepository:
    return GoalRepository(_data_dir() / "goals.jsonl")


def _render_questions(questions: list[Question]) -> None:
    st.caption(f"{len(questions)} question{'s' if len(questions) != 1 else ''}")

    if not questions:
        st.info("No questions found.")

    for question in questions:
        with st.container(border=True):
            st.markdown(question.content)
            st.caption(question.created_at.strftime("%Y-%m-%d %H:%M"))
            with st.expander("Reveal answer"):
                st.write(question.answer)


def questions_page() -> None:
    semantic_search = _get_semantic_search()
    semantic_search.drop()
    repository = _question_repository(semantic_search)
    all_questions = repository.load_all()

    search_query = st.text_input("Search", placeholder="Search questions by topic...")
    if search_query:
        questions = repository.search_by_topic(search_query)
    else:
        questions = sorted(all_questions, key=lambda q: q.created_at, reverse=True)

    _render_questions(questions)


def goals_page() -> None:
    repository = _goal_repository()

    with st.form("add_goal", clear_on_submit=True):
        goal_content = st.text_input("New goal", placeholder="e.g. Learn how retries are handled")
        if st.form_submit_button("Add goal") and goal_content.strip():
            repository.save(Goal(content=goal_content.strip()))
            st.rerun()

    goals = sorted(repository.load_all(), key=lambda g: g.created_at, reverse=True)
    st.caption(f"{len(goals)} goal{'s' if len(goals) != 1 else ''}")

    if not goals:
        st.info("No goals yet.")

    for goal in goals:
        if st.button(goal.content, key=str(goal.id), use_container_width=True):
            st.session_state["selected_goal_id"] = str(goal.id)
            st.switch_page(GOAL_QUESTIONS_PAGE)


def goal_questions_page() -> None:
    goal_id = st.session_state.get("selected_goal_id")
    goal = next((g for g in _goal_repository().load_all() if str(g.id) == goal_id), None)

    if st.button("← Back to goals"):
        st.switch_page(GOALS_PAGE)

    if goal is None:
        st.warning("Goal not found.")
        return

    st.subheader(goal.content)

    semantic_search = _get_semantic_search()
    semantic_search.drop()
    repository = _question_repository(semantic_search)

    _render_questions(repository.search_by_topic(goal.content))


st.set_page_config(page_title="Knowledge Base", page_icon="🧠", layout="centered")

if not _authorized():
    st.stop()

QUESTIONS_PAGE = st.Page(questions_page, title="Questions", icon="❓", default=True)
GOALS_PAGE = st.Page(goals_page, title="Goals", icon="🎯")
GOAL_QUESTIONS_PAGE = st.Page(goal_questions_page, title="Goal", url_path="goal", visibility="hidden")

navigation = st.navigation([QUESTIONS_PAGE, GOALS_PAGE, GOAL_QUESTIONS_PAGE], position="top")
navigation.run()
