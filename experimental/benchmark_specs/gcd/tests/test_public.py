from gcd import gcd
import pytest

@pytest.mark.parametrize("a,b,want", [
    (5,0,5), (35,21,7), (18,24,6), (10,5,5), (17,13,1), (0,5,5)
])
def test_common_divisor(a,b,want):
    assert gcd(a,b) == want
