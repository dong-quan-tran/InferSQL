from __future__ import annotations


class InferSQLError(Exception):
    """Base class for domain-specific errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BadRequestError(InferSQLError):
    """Represents a 400-style client error."""


class NotFoundError(InferSQLError):
    """Represents a 404-style error."""


class EmptyQueryError(BadRequestError):
    """SQL string is blank or only whitespace."""


class InvalidQuerySyntaxError(BadRequestError):
    """SQL string could not be parsed."""


class UnsupportedQueryError(BadRequestError):
    """Query type or structure is not supported."""


class UnknownDatasetError(NotFoundError):
    """Referenced dataset does not exist."""


class UnknownColumnError(BadRequestError):
    """Referenced column does not exist on the dataset."""