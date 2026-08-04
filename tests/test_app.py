from app import add, greet, multiply


def test_add() -> None:
    assert add(2, 3) == 5


def test_add_negative() -> None:
    assert add(-1, 1) == 0


def test_multiply() -> None:
    assert multiply(3, 4) == 12


def test_multiply_zero() -> None:
    assert multiply(5, 0) == 0


def test_greet() -> None:
    assert greet("Novus") == "Hello, Novus!"
