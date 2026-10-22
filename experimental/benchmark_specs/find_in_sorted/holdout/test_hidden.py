from find_in_sorted import find_in_sorted
import pytest
@pytest.mark.parametrize("arr,target", [
    ([1,5,10,20],21),([0,1,2,3,4,5],5),([0,1,2,3,4,5],0),
    ([0,1,2,3,4,5],4),([5,10,15,20,25,30],25),
    ([10,20,30,40,50],99),([2,4,6,8],3)
])
def test_search_properties(arr,target):
    actual=find_in_sorted(arr,target)
    if target in arr:
        assert 0 <= actual < len(arr) and arr[actual]==target
    else:
        assert actual == -1
