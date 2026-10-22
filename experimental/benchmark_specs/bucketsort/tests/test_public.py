from bucketsort import bucketsort
import pytest

@pytest.mark.parametrize("arr,k", [
    ([],5),([0],1),([2,0,1],3),([3,1,2,1],4),
    ([0,0,2,2],3),([1,1,1],3),([4,1,0,3,2],5)
])
def test_sort_public(arr,k):
    assert bucketsort(arr,k) == sorted(arr)
