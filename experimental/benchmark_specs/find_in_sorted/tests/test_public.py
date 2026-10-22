from find_in_sorted import find_in_sorted
import pytest
@pytest.mark.parametrize("arr,target,expected", [
    ([],5,-1),([1],1,0),([1],2,-1),([1,2,3,4],4,3),
    ([1,3,5,7,9],9,4),([1,2,3,4,5],3,2),
    ([3,4,5,6],2,-1)
])
def test_binary_search(arr,target,expected):
    assert find_in_sorted(arr,target) == expected
