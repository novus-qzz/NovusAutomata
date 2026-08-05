"""Tests for the demo app module."""

from __future__ import annotations

from app import add, greet, multiply


def test_add_positive() -> None:
    assert add(2, 3) == 5


def test_add_negative() -> None:
    assert add(-1, -2) == -3


def test_multiply() -> None:
    assert multiply(4, 5) == 20


def test_multiply_zero() -> None:
    assert multiply(0, 10) == 0


def test_greet() -> None:
    assert greet("Alice") == "Hello, Alice!"


def test_greet_blank() -> None:
    assert greet("") == "Hello, world!"


def test_greet_whitespace() -> None:
    assert greet("  Bob  ") == "Hello, Bob!"
