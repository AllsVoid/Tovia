from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.finance import Expense
from app.schemas.finance import BookingCreate, ExpenseCreate
from app.services.finance import expense_summary


def expense(**overrides: object) -> ExpenseCreate:
    return ExpenseCreate.model_validate(
        {
            "original_amount": "0.1",
            "original_currency": "CNY",
            "occurred_at": "2026-10-01T09:00:00+08:00",
            **overrides,
        }
    )


@pytest.mark.parametrize(
    "value", [0.1, True, "NaN", "Infinity", "-1", "0.00001", "100000000000000"]
)
def test_money_rejects_lossy_or_out_of_range_input(value: object) -> None:
    with pytest.raises(ValidationError):
        expense(original_amount=value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"original_currency": "ZZZ"},
        {"original_currency": "usd"},
        {"settled_amount": "1"},
        {"settled_currency": "USD"},
        {"exchange_rate": "0.1"},
        {"settled_amount": "1", "settled_currency": "USD", "exchange_rate": "0"},
        {"settled_amount": "1", "settled_currency": "USD", "exchange_rate": "0.123456789"},
        {"occurred_at": "2026-10-01T09:00:00"},
        {"timezone": "wrong/timezone"},
        {"category": " "},
        {"user_id": "00000000-0000-4000-8000-000000000001"},
    ],
)
def test_expense_relationships_and_metadata_validation(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        expense(**overrides)


def test_booking_time_and_money_pairs() -> None:
    base = {
        "type": "FLIGHT",
        "title": "Return flight",
        "start_at": "2026-10-02T10:00:00+09:00",
        "end_at": "2026-10-02T09:30:00+08:00",
    }
    assert BookingCreate.model_validate(base).type == "FLIGHT"
    for patch in (
        {"end_at": "2026-10-02T08:59:00+08:00"},
        {"amount": "10"},
        {"type": "UNKNOWN"},
        {"status": "UNKNOWN"},
        {"title": " "},
    ):
        with pytest.raises(ValidationError):
            BookingCreate.model_validate({**base, **patch})


@pytest.mark.parametrize(
    "kind", ["FLIGHT", "TRAIN", "BUS", "HOTEL", "TICKET", "RESTAURANT", "OTHER"]
)
def test_all_booking_types_are_supported(kind: str) -> None:
    assert (
        BookingCreate.model_validate(
            {"type": kind, "title": "Booking", "start_at": "2026-10-01T00:00:00Z"}
        ).type
        == kind
    )


def test_summary_uses_decimals_separates_currencies_and_never_double_counts() -> None:
    rows = [
        Expense(original_amount=Decimal("0.1"), original_currency="USD", category="FOOD"),
        Expense(original_amount=Decimal("0.2"), original_currency="USD", category="FOOD"),
        Expense(
            original_amount=Decimal("1200"),
            original_currency="JPY",
            settled_amount=Decimal("60.4321"),
            settled_currency="CNY",
            category="FOOD",
        ),
        Expense(
            original_amount=Decimal("5"),
            original_currency="CNY",
            settled_amount=Decimal("0"),
            settled_currency="CNY",
            category="HOTEL",
        ),
    ]
    summary = expense_summary(3, rows)
    assert summary.booking_count == 3
    assert {m.currency: m.amount for m in summary.original_totals} == {
        "USD": Decimal("0.3"),
        "JPY": Decimal("1200"),
        "CNY": Decimal("5"),
    }
    assert {m.currency: m.amount for m in summary.paid_totals} == {
        "USD": Decimal("0.3"),
        "CNY": Decimal("60.4321"),
    }
    assert {(m.category, m.currency): m.amount for m in summary.categories} == {
        ("FOOD", "USD"): Decimal("0.3"),
        ("FOOD", "CNY"): Decimal("60.4321"),
        ("HOTEL", "CNY"): Decimal("0"),
    }
    assert expense_summary(0, []).paid_totals == []
    assert '"0.3"' in summary.model_dump_json()
