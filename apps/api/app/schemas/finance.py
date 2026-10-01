from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import AfterValidator, AwareDatetime, BeforeValidator, Field, model_validator

from app.models.finance import BookingStatus, BookingType
from app.schemas.core import Input, Timezone, Title


def exact_decimal(value: object) -> object:
    if isinstance(value, (float, bool)):
        raise ValueError("Send decimal values as strings, never floating point numbers")
    return value


# ISO 4217 monetary currencies. No automatic conversion or minor-unit rounding.
CURRENCIES = frozenset(
    (
        "AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BOV BRL BSD "
        "BTN BWP BYN BZD CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUP CVE CZK DJF DKK DOP DZD "
        "EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD "
        "IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL "
        "MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN "
        "PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN "
        "SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD USN UYI UYU UYW UZS VED VES "
        "VND VUV WST XAF XCD XCG XOF XPF YER ZAR ZMW ZWG"
    ).split()
)


def currency_code(value: str) -> str:
    if value not in CURRENCIES:
        raise ValueError("Use a supported uppercase ISO 4217 currency code")
    return value


Currency = Annotated[str, AfterValidator(currency_code)]
Money = Annotated[
    Decimal,
    BeforeValidator(exact_decimal),
    Field(
        ge=0, lt=Decimal("100000000000000"), max_digits=18, decimal_places=4, allow_inf_nan=False
    ),
]
Rate = Annotated[
    Decimal,
    BeforeValidator(exact_decimal),
    Field(gt=0, lt=Decimal("10000000000"), max_digits=18, decimal_places=8, allow_inf_nan=False),
]
ShortText = Annotated[str, Field(min_length=1, max_length=200)]
Note = Annotated[str, Field(max_length=10000)]
Version = Annotated[int, Field(ge=1, strict=True)]


class BookingCreate(Input):
    trip_id: UUID | None = None
    activity_id: UUID | None = None
    type: BookingType
    status: BookingStatus = BookingStatus.CONFIRMED
    title: Title
    provider_name: ShortText | None = None
    reference_no: ShortText | None = None
    start_at: AwareDatetime
    end_at: AwareDatetime | None = None
    timezone: Timezone = "UTC"
    end_timezone: Timezone = "UTC"
    origin_place_id: UUID | None = None
    destination_place_id: UUID | None = None
    address: Note | None = None
    amount: Money | None = None
    currency: Currency | None = None
    note: Note | None = None

    @model_validator(mode="after")
    def valid_booking(self) -> Self:
        if self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("end_at must be on or after start_at")
        if (self.amount is None) != (self.currency is None):
            raise ValueError("amount and currency must be supplied together")
        if self.activity_id is not None and self.trip_id is None:
            raise ValueError("activity_id requires trip_id")
        return self


class BookingPatch(Input):
    version: Version
    trip_id: UUID | None = None
    activity_id: UUID | None = None
    type: BookingType | None = None
    status: BookingStatus | None = None
    title: Title | None = None
    provider_name: ShortText | None = None
    reference_no: ShortText | None = None
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    timezone: Timezone | None = None
    end_timezone: Timezone | None = None
    origin_place_id: UUID | None = None
    destination_place_id: UUID | None = None
    address: Note | None = None
    amount: Money | None = None
    currency: Currency | None = None
    note: Note | None = None


class BookingRead(BookingCreate):
    id: UUID
    user_id: UUID
    version: Version
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ExpenseCreate(Input):
    trip_id: UUID | None = None
    trip_day_id: UUID | None = None
    activity_id: UUID | None = None
    place_id: UUID | None = None
    merchant: ShortText | None = None
    category: Annotated[str, Field(min_length=1, max_length=64)] = "OTHER"
    original_amount: Money
    original_currency: Currency
    settled_amount: Money | None = None
    settled_currency: Currency | None = None
    exchange_rate: Rate | None = None
    payment_method: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    occurred_at: AwareDatetime
    timezone: Timezone = "UTC"
    note: Note | None = None

    @model_validator(mode="after")
    def valid_expense(self) -> Self:
        if (self.settled_amount is None) != (self.settled_currency is None):
            raise ValueError("settled_amount and settled_currency must be supplied together")
        if self.exchange_rate is not None and self.settled_amount is None:
            raise ValueError("exchange_rate requires settlement")
        if (self.trip_day_id or self.activity_id) and not self.trip_id:
            raise ValueError("day/activity requires trip_id")
        return self


class ExpensePatch(Input):
    version: Version
    trip_id: UUID | None = None
    trip_day_id: UUID | None = None
    activity_id: UUID | None = None
    place_id: UUID | None = None
    merchant: ShortText | None = None
    category: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    original_amount: Money | None = None
    original_currency: Currency | None = None
    settled_amount: Money | None = None
    settled_currency: Currency | None = None
    exchange_rate: Rate | None = None
    payment_method: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    occurred_at: AwareDatetime | None = None
    timezone: Timezone | None = None
    note: Note | None = None


class ExpenseRead(ExpenseCreate):
    id: UUID
    user_id: UUID
    version: Version
    created_at: AwareDatetime
    updated_at: AwareDatetime


class MoneyTotal(Input):
    currency: str
    amount: Decimal


class CategoryTotal(MoneyTotal):
    category: str


class TripSummary(Input):
    booking_count: int
    expense_count: int
    original_totals: list[MoneyTotal]
    paid_totals: list[MoneyTotal]
    categories: list[CategoryTotal]
