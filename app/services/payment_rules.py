from collections.abc import Mapping


VALID_INSTALLMENT_MONTHS = frozenset({3, 6, 12})
ALLOWED_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "pending": frozenset({"succeeded", "failed"}),
    "succeeded": frozenset({"refunded"}),
    "failed": frozenset(),
    "refunded": frozenset(),
}


def calculate_discount(price: int, promo_code: str | None) -> tuple[int, int]:
    if promo_code is None:
        return 0, price
    if promo_code.upper() != "KVITTO10":
        raise ValueError("Unknown promo code")
    discount = price // 10
    return discount, price - discount


def build_schedule(amount: int, months: int) -> list[int]:
    if months not in VALID_INSTALLMENT_MONTHS:
        raise ValueError("Installment months must be 3, 6, or 12")
    base, remainder = divmod(amount, months)
    return [base + (1 if index < remainder else 0) for index in range(months)]


def is_valid_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
