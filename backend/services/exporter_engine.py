from agents.vendor import check_vendor_payment
from agents.compliance import check_export_compliance
from agents.commerce import create_order
from services.risk_engine import calculate_risk


# ============================================================
# AURA EXPORTER ENGINE
# Autonomous Unified Razorpay Agent
#
# Central execution layer between:
#
#     AURA Brain
#          ↓
#     Exporter Engine
#          ↓
#     Vendor / Compliance / Commerce
#          ↓
#     Risk Engine
#
# This file keeps agent execution modular and predictable.
# ============================================================


# ============================================================
# VENDOR AGENT
# ============================================================

def run_vendor_check(vendor_data: dict):
    """
    Run the Vendor Agent.

    Expected vendor_data:

        {
            "invoice_amount": 50000,
            "invoice_date": "2026-09-03",
            "is_msme": True,
            "has_written_agreement": False
        }
    """

    if not vendor_data:
        raise ValueError(
            "Vendor data is required."
        )

    if "invoice_amount" not in vendor_data:
        raise ValueError(
            "Vendor invoice amount is required."
        )

    if "invoice_date" not in vendor_data:
        raise ValueError(
            "Vendor invoice date is required."
        )

    if "is_msme" not in vendor_data:
        raise ValueError(
            "MSME status is required."
        )

    return check_vendor_payment(
        invoice_amount=vendor_data["invoice_amount"],
        invoice_date=vendor_data["invoice_date"],
        is_msme=vendor_data["is_msme"],
        has_written_agreement=vendor_data.get(
            "has_written_agreement",
            False,
        ),
    )


# ============================================================
# COMPLIANCE AGENT
# ============================================================

def run_compliance_check(compliance_data: dict):
    """
    Run the Compliance Agent.

    Missing fields default to False because the compliance
    engine treats missing evidence as unavailable.
    """

    if compliance_data is None:
        compliance_data = {}

    return check_export_compliance(
        shipping_bill=compliance_data.get(
            "shipping_bill",
            False,
        ),
        invoice=compliance_data.get(
            "invoice",
            False,
        ),
        gst_lut=compliance_data.get(
            "gst_lut",
            False,
        ),
        edpms_realized=compliance_data.get(
            "edpms_realized",
            False,
        ),
        e_firc=compliance_data.get(
            "e_firc",
            False,
        ),
    )


# ============================================================
# COMMERCE AGENT
# ============================================================

def run_payment(
    service: str,
    amount: float,
    currency: str = "INR",
):
    """
    Prepare a Razorpay order.

    IMPORTANT:
    This function creates an order only.

    It does NOT:
        - capture money
        - automatically charge a customer
        - bypass checkout
        - bypass human approval

    Final payment remains behind the Razorpay checkout /
    approval flow.
    """

    if not service:
        service = "AURA Exporter Service"

    if amount is None:
        raise ValueError(
            "Payment amount is required."
        )

    amount = float(amount)

    if amount <= 0:
        raise ValueError(
            "Payment amount must be greater than zero."
        )

    return create_order(
        service=service,
        hours=1,
        rate=amount,
        currency=currency,
    )


# ============================================================
# RISK COLLECTION
# ============================================================

def collect_agent_risks(results: dict):
    """
    Collect risk signals from every executed agent.

    Vendor:
        43B_h_risk

    Compliance:
        risk
    """

    risks = []

    if not results:
        return risks

    vendor_result = results.get("vendor")

    if vendor_result:
        vendor_risk = vendor_result.get(
            "43B_h_risk"
        )

        if vendor_risk:
            risks.append(
                str(vendor_risk).upper()
            )

    compliance_result = results.get("compliance")

    if compliance_result:
        compliance_risk = compliance_result.get(
            "risk"
        )

        if compliance_risk:
            risks.append(
                str(compliance_risk).upper()
            )

    return risks


# ============================================================
# UNIFIED RISK ENGINE
# ============================================================

def calculate_unified_risk(results: dict):
    """
    Combine all agent risks into one AURA risk result.
    """

    risks = collect_agent_risks(results)

    return calculate_risk(risks)


# ============================================================
# PAYMENT DECISION
# ============================================================

def make_payment_decision(results: dict):
    """
    Convert agent results into an actionable decision.

    HIGH:
        BLOCK_PAYMENT

    MEDIUM:
        REVIEW_REQUIRED

    LOW:
        PAYMENT_READY

    AURA always requires human approval before final
    payment execution.
    """

    risk = calculate_unified_risk(results)

    level = risk["risk_level"]

    if level == "HIGH":
        return {
            "decision": "BLOCK_PAYMENT",
            "approval_required": True,
            "execution_allowed": False,
            "risk": risk,
            "reason": (
                "High risk detected. "
                "Payment must be blocked until "
                "the outstanding risk is resolved."
            ),
        }

    if level == "MEDIUM":
        return {
            "decision": "REVIEW_REQUIRED",
            "approval_required": True,
            "execution_allowed": False,
            "risk": risk,
            "reason": (
                "Medium risk detected. "
                "Human review is required before "
                "the payment can proceed."
            ),
        }

    return {
        "decision": "PAYMENT_READY",
        "approval_required": True,
        "execution_allowed": True,
        "risk": risk,
        "reason": (
            "No high-risk blocker detected. "
            "Payment can be prepared, but human "
            "approval is still required."
        ),
    }


# ============================================================
# COMPLETE EXPORTER ANALYSIS
# ============================================================

def run_exporter_analysis(
    vendor_data: dict | None = None,
    compliance_data: dict | None = None,
):
    """
    Run the available exporter intelligence agents.

    This function is useful for:
        - dashboard analysis
        - API testing
        - future Brain orchestration
        - combined risk analysis
    """

    results = {}
    execution = []

    # --------------------------------------------------------
    # Vendor
    # --------------------------------------------------------

    if vendor_data:

        execution.append({
            "agent": "vendor",
            "action": (
                "Checking MSME payment deadline "
                "and Section 43B(h)"
            ),
            "status": "running",
        })

        try:

            vendor_result = run_vendor_check(
                vendor_data
            )

            results["vendor"] = vendor_result

            execution.append({
                "agent": "vendor",
                "action": "Vendor analysis completed",
                "status": "completed",
            })

        except Exception as exc:

            results["vendor_error"] = str(exc)

            execution.append({
                "agent": "vendor",
                "action": f"Vendor analysis failed: {str(exc)}",
                "status": "failed",
            })

    # --------------------------------------------------------
    # Compliance
    # --------------------------------------------------------

    if compliance_data:

        execution.append({
            "agent": "compliance",
            "action": (
                "Checking export compliance "
                "requirements"
            ),
            "status": "running",
        })

        try:

            compliance_result = run_compliance_check(
                compliance_data
            )

            results["compliance"] = compliance_result

            execution.append({
                "agent": "compliance",
                "action": (
                    "Compliance analysis completed"
                ),
                "status": "completed",
            })

        except Exception as exc:

            results["compliance_error"] = str(exc)

            execution.append({
                "agent": "compliance",
                "action": (
                    f"Compliance analysis failed: {str(exc)}"
                ),
                "status": "failed",
            })

    # --------------------------------------------------------
    # Unified risk
    # --------------------------------------------------------

    aura_risk = calculate_unified_risk(
        results
    )

    results["aura_risk"] = aura_risk

    execution.append({
        "agent": "risk",
        "action": (
            f"Unified risk calculated as "
            f"{aura_risk['risk_level']}"
        ),
        "status": "completed",
    })

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    decision = make_payment_decision(
        results
    )

    results["decision"] = decision

    execution.append({
        "agent": "decision",
        "action": (
            f"Decision: "
            f"{decision['decision']}"
        ),
        "status": "completed",
    })

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    return {
        "agent": "aura",
        "name": "AURA",
        "expansion": (
            "Autonomous Unified Razorpay Agent"
        ),
        "status": "analysis_complete",
        "results": results,
        "execution": execution,
    }