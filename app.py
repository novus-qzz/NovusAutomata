"""NovusAutomata demo module — simple arithmetic and greeting functions."""

from __future__ import annotations


def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of *a* and *b*."""
    return a + b


def multiply(a: int | float, b: int | float) -> int | float:
    """Return the product of *a* and *b*."""
    return a * b


def greet(name: str) -> str:
    """Return a greeting string for *name*."""
    if not name or not name.strip():
        name = "world"
    return f"Hello, {name.strip()}!"
