from is_valid_parenthesization import is_valid_parenthesization as valid
import pytest
@pytest.mark.parametrize("s,expected", [
    ("((()()))()",True),("())(()",False),("(()())",True),("((())",False),
    ("()(()",False),(")()(",False),("(((())))",True),("(",False)
])
def test_balanced(s,expected):
    assert valid(s) is expected
