"""Kept out of the candidate-search loop; independent edge checks."""
from cart_rules import free_shipping, remaining_balance, can_view_record
import pytest

@pytest.mark.parametrize("total,member,expected", [
    (0, True, False), (1, True, False), (4998, True, False),
    (5000, True, True), (5001, True, True),
    (5000, False, False), (250000, False, False),
    (250000, True, True),
])
def test_shipping_edges(total, member, expected):
    assert free_shipping(total, member) is expected

@pytest.mark.parametrize("balance,payment,expected", [
    (250, 10, 240), (250, 249, 1), (250, 250, 0),
    (250, 251, 0), (0, 0, 0), (700, 100, 600),
])
def test_payment_edges(balance, payment, expected):
    assert remaining_balance(balance, payment) == expected

@pytest.mark.parametrize("active,owner,result", [
    (True, True, True), (True, False, False),
    (False, True, False), (False, False, False),
])
def test_access_matrix(active, owner, result):
    assert can_view_record(active, owner) is result
