from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PaymentRequest(BaseModel):
    service: str = Field(
        default="AURA Exporter Service",
        min_length=1,
        max_length=100
    )

    amount: float = Field(
        gt=0,
        description="Payment amount in major currency units"
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3
    )

    @field_validator("service")
    @classmethod
    def validate_service(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Service cannot be empty.")

        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return value.strip().upper()


class VendorRequest(BaseModel):
    invoice_amount: float = Field(
        gt=0,
        description="Vendor invoice amount"
    )

    invoice_date: str = Field(
        min_length=10,
        max_length=10
    )

    is_msme: bool

    has_written_agreement: bool = False


class ComplianceRequest(BaseModel):
    shipping_bill: bool = False
    invoice: bool = False
    gst_lut: bool = False
    edpms_realized: bool = False
    e_firc: bool = False


class ExporterRequest(BaseModel):
    """
    Main AURA Brain request.

    AURA receives a natural-language request and can optionally
    receive structured payment, vendor and compliance information.
    """

    request: str = Field(
        min_length=1,
        max_length=2000,
        description="Natural-language exporter request"
    )

    payment: Optional[PaymentRequest] = None

    vendor: Optional[VendorRequest] = None

    compliance: Optional[ComplianceRequest] = None

    @field_validator("request")
    @classmethod
    def validate_request(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Request cannot be empty.")

        return value