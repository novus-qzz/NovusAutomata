from app import add, greet, multiply


def test_add():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, 1) == 0


def test_multiply():
    assert multiply(3, 4) == 12


def test_multiply_zero():
    assert multiply(5, 0) == 0


def test_greet():
    assert greet("Novus") == "Hello, Novus!"
