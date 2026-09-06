import hmac
import os
from pathlib import Path

import streamlit as st

from knowledge_base.api.auth import hash_token
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


@st.cache_resource
def _get_semantic_search() -> SemanticSearch:
    return SemanticSearch()


st.set_page_config(page_title="Knowledge Base", page_icon="🧠", layout="centered")

if not _authorized():
    st.stop()


repository = QuestionRepository(_data_dir() / "questions.jsonl")
all_questions = repository.load_all()

semantic_search = _get_semantic_search()
semantic_search.drop()
semantic_search.add(all_questions)

search_query = st.text_input("Search", placeholder="Search questions by topic...")
if search_query:
    questions = semantic_search.search(search_query)
else:
    questions = sorted(all_questions, key=lambda q: q.created_at, reverse=True)

st.caption(f"{len(questions)} question{'s' if len(questions) != 1 else ''}")

if not questions:
    st.info("No questions found.")

for question in questions:
    with st.container(border=True):
        st.markdown(question.content)
        st.caption(question.created_at.strftime("%Y-%m-%d %H:%M"))
        with st.expander("Reveal answer"):
            st.write(question.answer)
