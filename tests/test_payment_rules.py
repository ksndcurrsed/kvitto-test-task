import pytest

from app.services.payment_rules import (
    build_schedule,
    calculate_discount,
    is_valid_transition,
)


@pytest.mark.parametrize("code", ["KVITTO10", "kvitto10", "KvItTo10"])
def test_kvitto_promo_is_case_insensitive(code: str) -> None:
    assert calculate_discount(1_990_000, code) == (199_000, 1_791_000)


def test_no_promo_keeps_full_price() -> None:
    assert calculate_discount(990_000, None) == (0, 990_000)


def test_unknown_promo_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown promo code"):
        calculate_discount(990_000, "OTHER")


@pytest.mark.parametrize("months", [3, 6, 12])
def test_schedule_sums_exactly_with_remainder_first(months: int) -> None:
    schedule = build_schedule(1_990_000, months)
    assert len(schedule) == months
    assert sum(schedule) == 1_990_000
    assert schedule == [663_334, 663_333, 663_333] if months == 3 else schedule


def test_invalid_installment_term_is_rejected() -> None:
    with pytest.raises(ValueError, match="3, 6, or 12"):
        build_schedule(100, 5)


@pytest.mark.parametrize(
    ("current", "target", "allowed"),
    [
        ("pending", "succeeded", True),
        ("pending", "failed", True),
        ("succeeded", "refunded", True),
        ("pending", "refunded", False),
        ("failed", "pending", False),
        ("refunded", "succeeded", False),
    ],
)
def test_status_transition_matrix(current: str, target: str, allowed: bool) -> None:
    assert is_valid_transition(current, target) is allowed
