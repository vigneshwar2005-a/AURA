import os
import razorpay
from dotenv import load_dotenv


load_dotenv()


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")


if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError(
        "Razorpay API credentials are missing. "
        "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"
    )


client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)


def create_order(
    service: str,
    hours: int,
    rate: float,
    currency: str = "INR"
):
    """
    AURA Commerce Agent

    Creates a Razorpay order in the configured Razorpay mode.

    IMPORTANT:
    This function creates an order only.
    It does NOT capture or transfer money automatically.
    """

    if not service or not str(service).strip():
        service = "AURA Exporter Service"

    if hours <= 0:
        raise ValueError("Hours must be greater than zero.")

    if rate <= 0:
        raise ValueError("Rate must be greater than zero.")

    currency = str(currency).upper().strip()

    if len(currency) != 3:
        raise ValueError("Currency must be a valid 3-letter code.")

    total = hours * rate

    # Razorpay expects amount in the smallest currency unit.
    amount = int(round(total * 100))

    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    receipt = f"AURA-{hours}-{int(rate)}"

    order_data = {
        "amount": amount,
        "currency": currency,
        "receipt": receipt,
        "notes": {
            "service": str(service),
            "hours": str(hours),
            "agent": "AURA Commerce Agent"
        }
    }

    order = client.order.create(order_data)

    return {
        "status": "order_created",
        "service": service,
        "hours": hours,
        "rate": rate,
        "currency": currency,
        "total": total,
        "amount_subunits": amount,
        "razorpay_order_id": order["id"],
        "razorpay_status": order["status"],
        "payment_action": "HUMAN_APPROVAL_REQUIRED",
        "message": (
            "Razorpay order created successfully. "
            "Payment requires human approval through the checkout flow."
        )
    }


def get_payment_readiness(
    risk_level: str,
    decision: str
):
    """
    Determine whether AURA should allow the payment flow.

    AURA never bypasses the human approval gate.
    """

    risk_level = str(risk_level).upper().strip()
    decision = str(decision).upper().strip()

    if risk_level == "HIGH" or decision == "BLOCK_PAYMENT":
        return {
            "payment_ready": False,
            "decision": "BLOCK_PAYMENT",
            "approval_required": True,
            "message": (
                "Payment is blocked because a high-risk condition "
                "was detected."
            )
        }

    if risk_level == "MEDIUM" or decision == "REVIEW_REQUIRED":
        return {
            "payment_ready": False,
            "decision": "REVIEW_REQUIRED",
            "approval_required": True,
            "message": (
                "Payment requires human review before proceeding."
            )
        }

    return {
        "payment_ready": True,
        "decision": "PAYMENT_READY",
        "approval_required": True,
        "message": (
            "Payment is eligible to proceed, subject to human approval."
        )
    }