from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PaymentMethod(str, Enum):
    card = "card"
    sbp = "sbp"
    installment = "installment"


class PaymentStatus(str, Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"


class TariffResponse(BaseModel):
    id: int
    title: str
    price: int

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    tariff_id: int = Field(gt=0)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    method: PaymentMethod
    installment_months: int | None = None
    promo_code: str | None = None

    @model_validator(mode="after")
    def validate_installments(self) -> "PaymentCreate":
        if self.method == PaymentMethod.installment and self.installment_months not in {3, 6, 12}:
            raise ValueError("installment_months must be 3, 6, or 12 for installment payments")
        if self.method != PaymentMethod.installment and self.installment_months is not None:
            raise ValueError("installment_months is only allowed for installment payments")
        return self


class PaymentResponse(BaseModel):
    id: int
    status: PaymentStatus
    tariff_id: int
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BankWebhook(BaseModel):
    payment_id: int = Field(gt=0)
    status: PaymentStatus
