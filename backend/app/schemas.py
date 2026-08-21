"""Pydantic schemas for request/response models."""
from __future__ import annotations

from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str
