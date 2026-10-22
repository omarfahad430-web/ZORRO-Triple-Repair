from bucketsort import bucketsort
import pytest
@pytest.mark.parametrize("arr,k", [
    ([7,4,7,1,0],8),([0,0,0,1],2),([6,5,4,3,2,1,0],7),
    ([2]*8 + [1]*3 + [0],3),([9,8,9,2,1,0],10)
])
def test_sort_holdout(arr,k):
    assert bucketsort(arr,k) == sorted(arr)
