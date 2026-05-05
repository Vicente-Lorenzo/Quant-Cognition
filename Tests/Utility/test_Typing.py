from dataclasses import dataclass
from Library.Utility.Typing import (
    cast,
    equals,
    contains,
    hasmember,
    hasmethod,
    getmethod,
    hasproperty,
    getproperty,
    hasattribute,
    getattribute
)
def test_hasmember():
    class Base:
        y = 2
        def f(self):
            return 1
        @property
        def p(self):
            return 10
    class Child(Base):
        z = 3
    c = Child()
    c.x = 1
    assert hasmember(c, "x") is True
    assert hasmember(c, "z") is True
    assert hasmember(c, "f", mro=False) is False
    assert hasmember(c, "f", mro=True) is True
    assert hasmember(c, "p", mro=True) is True
def test_hasmember_slots():
    class S:
        __slots__ = ("x",)
        def __init__(self):
            self.x = 5
    s = S()
    assert hasmember(s, "x", slots=True) is True
    assert hasmember(s, "x", slots=False) is False
    assert hasmember(S, "x", slots=True) is True
    assert hasmember(S, "x", slots=False) is False
def test_attribute():
    class A:
        def __init__(self):
            self.x = 1
    a = A()
    assert hasattribute(a, "x") is True
    assert getattribute(a, "x") == 1
    assert hasattribute(A, "x") is False
    assert getattribute(A, "x") is None
def test_attribute_mro():
    class Base:
        y = 2
    class Child(Base):
        pass
    assert hasattribute(Child, "y", mro=False) is False
    assert hasattribute(Child, "y", mro=True) is True
    assert getattribute(Child, "y", mro=True) == 2
def test_method():
    class A:
        z = 3
        def f(self):
            return 1
        @staticmethod
        def s():
            return 2
        @classmethod
        def c(cls):
            return 3
    assert hasattribute(A, "z") is True
    assert hasattribute(A, "f") is False
    assert hasattribute(A, "s") is False
    assert hasattribute(A, "c") is False
    assert hasmethod(A, "f") is True
    assert hasmethod(A, "s") is True
    assert hasmethod(A, "c") is True
def test_method_binding():
    class A:
        def f(self):
            return 10
        @classmethod
        def c(cls):
            return cls.__name__
        @staticmethod
        def s():
            return 7
    a = A()
    mf = getmethod(a, "f")
    assert callable(mf) is True
    assert mf() == 10
    mc = getmethod(a, "c")
    assert callable(mc) is True
    assert mc() == "A"
    ms = getmethod(a, "s")
    assert callable(ms) is True
    assert ms() == 7
def test_property():
    class A:
        @property
        def p(self):
            return 10
    a = A()
    assert hasattribute(A, "p") is False
    assert hasmethod(A, "p") is False
    assert hasproperty(A, "p") is True
    assert hasproperty(a, "p") is True
    assert isinstance(getproperty(A, "p"), property) is True
    assert isinstance(getproperty(a, "p"), property) is True
def test_slots():
    class S:
        __slots__ = ("x",)
        def __init__(self):
            self.x = 5
    s = S()
    assert hasattribute(s, "x", slots=True) is True
    assert getattribute(s, "x", slots=True) == 5
    assert hasattribute(s, "x", slots=False) is False
    assert getattribute(s, "x", slots=False) is None
    assert hasattribute(S, "x", slots=True) is True
    assert hasattribute(S, "x", slots=False) is False
def test_slots_mro():
    class Base:
        __slots__ = ("b",)
        def __init__(self):
            self.b = 1
    class Child(Base):
        __slots__ = ("c",)
        def __init__(self):
            super().__init__()
            self.c = 2
    ch = Child()
    assert hasattribute(ch, "b", slots=True, mro=False) is False
    assert hasattribute(ch, "c", slots=True, mro=False) is True
    assert hasattribute(ch, "b", slots=True, mro=True) is True
    assert hasattribute(ch, "c", slots=True, mro=True) is True
def test_callable_method():
    class A:
        pass
    a = A()
    a.fun = lambda: 123
    assert hasattribute(a, "fun") is False
    assert hasmethod(a, "fun") is True
    assert getmethod(a, "fun")() == 123
def test_dataclass_slots():
    @dataclass(slots=True)
    class D:
        x: int
    d = D(7)
    assert hasattribute(d, "x", slots=True) is True
    assert getattribute(d, "x", slots=True) == 7
    assert hasattribute(d, "x", slots=False) is False
    assert getattribute(d, "x", slots=False) is None
    assert hasattribute(D, "x", slots=True) is True
    assert hasattribute(D, "x", slots=False) is False
def test_cast():
    assert cast("123", int, 0) == 123
    assert cast(123, int, 0) == 123
    assert cast("nope", int, 0) == 0
    assert cast(None, int, 0) == 0
def test_equals():
    assert equals(1.0, 1.0) is True
    assert equals(1.0, 1.0 + 1e-13) is True
    assert equals(1.0, 1.0 + 1e-6) is False
def test_contains():
    assert contains("Hello World", "world") is True
    assert contains("Hello World", "WORLD") is True
    assert contains("Hello World", "WORLD", case_sensitive=True) is False
    assert contains("Hello World", ("bye", "world")) is True
    assert contains("Hello World", ["bye", "mars"]) is False