import pytest

from app.services.safe_expr import UnsafeConditionError, safe_eval


def test_constants_and_arithmetic():
    assert safe_eval("1 + 2 * 3", {}) == 7
    assert safe_eval("(10 - 4) / 2", {}) == 3.0


def test_variable_lookup_and_comparison():
    assert safe_eval("count > 5", {"count": 7}) is True
    assert safe_eval("name == 'echo'", {"name": "echo"}) is True


def test_chained_comparison():
    assert safe_eval("0 < x < 10", {"x": 5}) is True
    assert safe_eval("0 < x < 10", {"x": 100}) is False


def test_boolean_ops():
    assert safe_eval("a and b", {"a": True, "b": True}) is True
    assert safe_eval("a or b", {"a": False, "b": True}) is True
    assert safe_eval("not flag", {"flag": False}) is True


def test_membership():
    assert safe_eval("x in items", {"x": 2, "items": [1, 2, 3]}) is True
    assert safe_eval("'a' not in items", {"items": ["b", "c"]}) is True


def test_subscript():
    assert safe_eval("data['k']", {"data": {"k": 42}}) == 42


def test_rejects_function_call():
    with pytest.raises(UnsafeConditionError):
        safe_eval("len([1,2,3])", {})


def test_rejects_attribute_access():
    with pytest.raises(UnsafeConditionError):
        safe_eval("x.upper()", {"x": "abc"})


def test_rejects_dunder_traversal():
    with pytest.raises(UnsafeConditionError):
        safe_eval("().__class__.__mro__[1].__subclasses__()", {})


def test_rejects_import():
    with pytest.raises(UnsafeConditionError):
        safe_eval("__import__('os').system('echo bad')", {})


def test_rejects_unknown_variable():
    with pytest.raises(UnsafeConditionError):
        safe_eval("foo > 1", {})


def test_rejects_reserved_identifier():
    with pytest.raises(UnsafeConditionError):
        safe_eval("__builtins__", {"__builtins__": {}})
