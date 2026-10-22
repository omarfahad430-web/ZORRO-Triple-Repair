from gcd import gcd
import math
import pytest

@pytest.mark.parametrize("a,b", [(2,3),(100,40),(81,27),(25,10),
                                 (1,1),(6,9),(0,7),(7,0),(63,84)])
def test_reference_gcd(a,b):
    assert gcd(a,b) == math.gcd(a,b)
