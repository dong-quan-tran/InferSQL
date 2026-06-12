# app/core/exceptions.py
from __future__ import annotations


class InferSQLError(Exception):
    """Base class for domain-specific errors."""


class BadRequestError(InferSQLError):
    """Represents a 400-style client error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(InferSQLError):
    """Represents a 404-style error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message