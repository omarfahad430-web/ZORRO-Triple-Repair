from is_valid_parenthesization import is_valid_parenthesization as valid
import pytest

@pytest.mark.parametrize("s,expected", [
    ("",True),("()",True),("(())",True),("(()",False),
    ("(((",False),(")(",False),("())",False),("()()",True)
])
def test_parentheses(s,expected):
    assert valid(s) is expected
