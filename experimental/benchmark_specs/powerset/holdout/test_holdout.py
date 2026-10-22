from powerset import powerset
import pytest
@pytest.mark.parametrize("items", [[0,1,2,3], [2], [1,2,3,4,5], []])
def test_power_cardinality(items):
    result=powerset(items)
    assert len(result) == 2**len(items)
    assert [] in result
    assert items in result
