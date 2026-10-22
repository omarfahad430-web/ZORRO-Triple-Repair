from powerset import powerset
import pytest
@pytest.mark.parametrize("items", [[], [1], [1,2], ["a","b","c"]])
def test_all_subsets(items):
    actual=powerset(items)
    expected={frozenset(items[j] for j in range(len(items)) if mask & (1 << j))
              for mask in range(1 << len(items))}
    assert {frozenset(x) for x in actual} == expected
    assert len(actual) == len(expected)
