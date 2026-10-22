"""Public regression suite; separate from the unseen holdout."""
from cart_rules import free_shipping, remaining_balance, can_view_record

def test_shipping_below_threshold():
    assert free_shipping(4999, True) is False

def test_shipping_exact_threshold():
    assert free_shipping(5000, True) is True

def test_shipping_above_threshold():
    assert free_shipping(9000, True) is True

def test_shipping_nonmember():
    assert free_shipping(8000, False) is False

def test_balance_partial():
    assert remaining_balance(1000, 300) == 700

def test_balance_full():
    assert remaining_balance(1000, 1000) == 0

def test_balance_excess():
    assert remaining_balance(1000, 1500) == 0

def test_balance_no_payment():
    assert remaining_balance(1000, 0) == 1000

def test_access_active_owner():
    assert can_view_record(True, True) is True

def test_access_inactive_owner():
    assert can_view_record(False, True) is False

def test_access_nonowner():
    assert can_view_record(True, False) is False

def test_access_neither():
    assert can_view_record(False, False) is False
