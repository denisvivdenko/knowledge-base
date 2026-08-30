from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    answer: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
