"""Small independent cart business-rule package, deliberately containing regressions."""
def free_shipping(total_cents: int, is_member: bool) -> bool:
    """Members qualify when order total is at least 5000 cents."""
    return total_cents > 5000 and is_member

def remaining_balance(balance_cents: int, paid_cents: int) -> int:
    """Total still outstanding after payment, floored at zero."""
    return max(0, balance_cents + paid_cents)

def can_view_record(account_active: bool, is_owner: bool) -> bool:
    """Only the active owner may access a record."""
    return account_active or is_owner
