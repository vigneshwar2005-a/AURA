from datetime import date, timedelta


def check_vendor_payment(
    invoice_amount: float,
    invoice_date: str,
    is_msme: bool,
    has_written_agreement: bool = False
):
    """
    AURA Vendor Agent

    Evaluates MSME vendor payment timelines and Section 43B(h)
    related payment risk.

    Rules used by this agent:
    - Non-Micro/Small Enterprise -> normal payment handling
    - Micro/Small Enterprise without written agreement -> 15 days
    - Micro/Small Enterprise with written agreement -> maximum 45 days
    """

    invoice = date.fromisoformat(invoice_date)
    today = date.today()

    # Non-MSME vendor
    if not is_msme:
        return {
            "agent": "vendor",
            "vendor_type": "Other Enterprise",
            "invoice_amount": invoice_amount,
            "invoice_date": invoice_date,
            "status": "NORMAL",
            "risk": "LOW",
            "43B_h_risk": "LOW",
            "payment_limit_days": None,
            "due_date": None,
            "days_remaining": None,
            "decision": "PAYMENT_READY",
            "message": (
                "Vendor is not identified as a Micro or Small Enterprise. "
                "The MSME-specific payment limit check is not triggered."
            ),
            "recommended_action": (
                "Proceed according to the normal vendor payment process."
            )
        }

    # MSME payment limit
    max_days = 45 if has_written_agreement else 15

    due_date = invoice + timedelta(days=max_days)
    days_remaining = (due_date - today).days

    # Overdue
    if today > due_date:
        status = "OVERDUE"
        risk = "HIGH"
        decision = "BLOCK_PAYMENT"

        message = (
            "MSME vendor payment is overdue and may create "
            "Section 43B(h) tax risk."
        )

        recommended_action = (
            "Escalate the payment immediately and review the "
            "tax impact before proceeding."
        )

    # Due within 5 days
    elif days_remaining <= 5:
        status = "DUE_SOON"
        risk = "MEDIUM"
        decision = "REVIEW_REQUIRED"

        message = (
            "The MSME vendor payment deadline is approaching."
        )

        recommended_action = (
            "Prioritize this payment and complete it before "
            "the applicable deadline."
        )

    # Still within limit
    else:
        status = "WITHIN_LIMIT"
        risk = "LOW"
        decision = "PAYMENT_READY"

        message = (
            "MSME vendor payment is currently within the "
            "applicable payment limit."
        )

        recommended_action = (
            "Payment can proceed while remaining within the "
            "applicable MSME payment timeline."
        )

    agreement_type = (
        "Written agreement"
        if has_written_agreement
        else "No written agreement"
    )

    return {
        "agent": "vendor",
        "vendor_type": "Micro/Small Enterprise",
        "invoice_amount": invoice_amount,
        "invoice_date": invoice_date,
        "agreement_status": agreement_type,
        "payment_limit_days": max_days,
        "due_date": str(due_date),
        "days_remaining": days_remaining,
        "status": status,
        "risk": risk,
        "43B_h_risk": risk,
        "decision": decision,
        "message": message,
        "recommended_action": recommended_action
    }